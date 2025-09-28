"""
Data cleanup background tasks for maintaining database health.

Provides tasks for cleaning up old data, removing orphaned records,
and optimizing database performance.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.orm import selectinload
import structlog

from ..models.players import Player
from ..models.matches import Match
from ..models.participants import MatchParticipant
from ..models.smurf_detection import SmurfDetection
from ..models.ranks import PlayerRank
from ..tasks.queue import BackgroundTask

logger = structlog.get_logger(__name__)


class DataCleanupTasks:
    """Background tasks for data cleanup and database maintenance."""

    def __init__(self, db: AsyncSession):
        """
        Initialize data cleanup tasks.

        Args:
            db: Database session
        """
        self.db = db

    async def cleanup_old_data(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up old data based on retention policies.

        Args:
            task_data: Task data containing cleanup parameters

        Returns:
            Dictionary with cleanup results
        """
        days_threshold = task_data.get('days_threshold', 90)
        dry_run = task_data.get('dry_run', False)
        batch_size = task_data.get('batch_size', 1000)

        logger.info("Cleaning up old data", days_threshold=days_threshold, dry_run=dry_run)

        try:
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            cleanup_results = {}

            # Clean up old match data
            match_cleanup = await self._cleanup_old_matches(cutoff_date, dry_run, batch_size)
            cleanup_results['matches'] = match_cleanup

            # Clean up old detection results
            detection_cleanup = await self._cleanup_old_detections(cutoff_date, dry_run, batch_size)
            cleanup_results['detections'] = detection_cleanup

            # Clean up old rank data
            rank_cleanup = await self._cleanup_old_ranks(cutoff_date, dry_run, batch_size)
            cleanup_results['ranks'] = rank_cleanup

            # Clean up inactive players
            player_cleanup = await self._cleanup_inactive_players(cutoff_date, dry_run, batch_size)
            cleanup_results['players'] = player_cleanup

            total_deleted = sum(result.get('deleted_count', 0) for result in cleanup_results.values())

            logger.info(
                "Old data cleanup completed",
                days_threshold=days_threshold,
                dry_run=dry_run,
                total_deleted=total_deleted,
                cleanup_results=cleanup_results
            )

            return {
                'days_threshold': days_threshold,
                'dry_run': dry_run,
                'total_deleted': total_deleted,
                'cleanup_results': cleanup_results,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to cleanup old data", error=str(e))
            raise

    async def cleanup_failed_detections(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up failed or incomplete detection results.

        Args:
            task_data: Task data containing cleanup parameters

        Returns:
            Dictionary with cleanup results
        """
        days_threshold = task_data.get('days_threshold', 7)
        max_retries = task_data.get('max_retries', 3)
        dry_run = task_data.get('dry_run', False)

        logger.info("Cleaning up failed detections", days_threshold=days_threshold)

        try:
            cutoff_date = datetime.now() - timedelta(days=days_threshold)

            # Find failed detection results
            query = select(SmurfDetection).where(
                and_(
                    SmurfDetection.last_analysis < cutoff_date,
                    or_(
                        SmurfDetection.games_analyzed == 0,
                        SmurfDetection.smurf_score == 0.0,
                        SmurfDetection.confidence.is_(None)
                    )
                )
            )

            result = await self.db.execute(query)
            failed_detections = result.scalars().all()

            if dry_run:
                logger.info("Dry run: would delete failed detections", count=len(failed_detections))
                return {
                    'dry_run': True,
                    'failed_detections_count': len(failed_detections),
                    'would_delete': len(failed_detections),
                    'timestamp': datetime.now().isoformat()
                }

            # Delete failed detections
            deleted_count = 0
            for detection in failed_detections:
                try:
                    await self.db.delete(detection)
                    deleted_count += 1
                except Exception as e:
                    logger.warning("Failed to delete detection", puuid=detection.puuid, error=str(e))

            await self.db.commit()

            logger.info(
                "Failed detections cleanup completed",
                deleted_count=deleted_count,
                total_found=len(failed_detections)
            )

            return {
                'dry_run': False,
                'failed_detections_count': len(failed_detections),
                'deleted_count': deleted_count,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to cleanup failed detections", error=str(e))
            await self.db.rollback()
            raise

    async def cleanup_orphaned_records(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up orphaned records in the database.

        Args:
            task_data: Task data containing cleanup parameters

        Returns:
            Dictionary with cleanup results
        """
        dry_run = task_data.get('dry_run', False)
        batch_size = task_data.get('batch_size', 500)

        logger.info("Cleaning up orphaned records", dry_run=dry_run)

        try:
            cleanup_results = {}

            # Clean up orphaned match participants
            participant_cleanup = await self._cleanup_orphaned_participants(dry_run, batch_size)
            cleanup_results['participants'] = participant_cleanup

            # Clean up orphaned rank records
            rank_cleanup = await self._cleanup_orphaned_ranks(dry_run, batch_size)
            cleanup_results['ranks'] = rank_cleanup

            # Clean up players with no activity
            player_cleanup = await self._cleanup_orphaned_players(dry_run, batch_size)
            cleanup_results['players'] = player_cleanup

            total_deleted = sum(result.get('deleted_count', 0) for result in cleanup_results.values())

            logger.info(
                "Orphaned records cleanup completed",
                dry_run=dry_run,
                total_deleted=total_deleted
            )

            return {
                'dry_run': dry_run,
                'total_deleted': total_deleted,
                'cleanup_results': cleanup_results,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to cleanup orphaned records", error=str(e))
            raise

    async def optimize_database(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform database optimization tasks.

        Args:
            task_data: Task data containing optimization parameters

        Returns:
            Dictionary with optimization results
        """
        vacuum_tables = task_data.get('vacuum_tables', True)
        analyze_tables = task_data.get('analyze_tables', True)
        update_statistics = task_data.get('update_statistics', True)

        logger.info("Optimizing database")

        try:
            optimization_results = {}

            # Update table statistics
            if update_statistics:
                stats_result = await self._update_table_statistics()
                optimization_results['statistics'] = stats_result

            # Vacuum tables (if supported)
            if vacuum_tables:
                vacuum_result = await self._vacuum_tables()
                optimization_results['vacuum'] = vacuum_result

            # Analyze tables for query optimization
            if analyze_tables:
                analyze_result = await self._analyze_tables()
                optimization_results['analyze'] = analyze_result

            logger.info(
                "Database optimization completed",
                results=optimization_results
            )

            return {
                'optimization_performed': True,
                'results': optimization_results,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to optimize database", error=str(e))
            raise

    async def cleanup_duplicate_records(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up duplicate records in the database.

        Args:
            task_data: Task data containing deduplication parameters

        Returns:
            Dictionary with deduplication results
        """
        dry_run = task_data.get('dry_run', False)
        table_name = task_data.get('table_name', 'all')

        logger.info("Cleaning up duplicate records", table=table_name, dry_run=dry_run)

        try:
            deduplication_results = {}

            if table_name in ['all', 'matches']:
                match_dedup = await self._deduplicate_matches(dry_run)
                deduplication_results['matches'] = match_dedup

            if table_name in ['all', 'players']:
                player_dedup = await self._deduplicate_players(dry_run)
                deduplication_results['players'] = player_dedup

            if table_name in ['all', 'detections']:
                detection_dedup = await self._deduplicate_detections(dry_run)
                deduplication_results['detections'] = detection_dedup

            total_deleted = sum(result.get('deleted_count', 0) for result in deduplication_results.values())

            logger.info(
                "Duplicate records cleanup completed",
                table=table_name,
                dry_run=dry_run,
                total_deleted=total_deleted
            )

            return {
                'table_name': table_name,
                'dry_run': dry_run,
                'total_deleted': total_deleted,
                'deduplication_results': deduplication_results,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to cleanup duplicate records", error=str(e))
            raise

    async def _cleanup_old_matches(self, cutoff_date: datetime, dry_run: bool, batch_size: int) -> Dict[str, Any]:
        """Clean up old match records."""
        # First delete related participants
        participant_query = delete(MatchParticipant).where(
            MatchParticipant.match_id.in_(
                select(Match.match_id).where(Match.game_creation < cutoff_date.timestamp() * 1000)
            )
        )

        if dry_run:
            result = await self.db.execute(
                select(func.count(MatchParticipant.match_id)).where(
                    MatchParticipant.match_id.in_(
                        select(Match.match_id).where(Match.game_creation < cutoff_date.timestamp() * 1000)
                    )
                )
            )
            count = result.scalar() or 0
            return {'table': 'match_participants', 'would_delete': count, 'deleted_count': 0}

        result = await self.db.execute(participant_query)
        deleted_participants = result.rowcount

        # Then delete matches
        match_query = delete(Match).where(Match.game_creation < cutoff_date.timestamp() * 1000)

        if dry_run:
            result = await self.db.execute(
                select(func.count(Match.match_id)).where(Match.game_creation < cutoff_date.timestamp() * 1000)
            )
            count = result.scalar() or 0
            return {'table': 'matches', 'would_delete': count, 'deleted_count': 0}

        result = await self.db.execute(match_query)
        deleted_matches = result.rowcount

        await self.db.commit()

        return {
            'table': 'matches',
            'deleted_matches': deleted_matches,
            'deleted_participants': deleted_participants,
            'deleted_count': deleted_matches + deleted_participants
        }

    async def _cleanup_old_detections(self, cutoff_date: datetime, dry_run: bool, batch_size: int) -> Dict[str, Any]:
        """Clean up old detection records."""
        query = delete(SmurfDetection).where(SmurfDetection.last_analysis < cutoff_date)

        if dry_run:
            result = await self.db.execute(
                select(func.count(SmurfDetection.id)).where(SmurfDetection.last_analysis < cutoff_date)
            )
            count = result.scalar() or 0
            return {'table': 'smurf_detections', 'would_delete': count, 'deleted_count': 0}

        result = await self.db.execute(query)
        deleted_count = result.rowcount
        await self.db.commit()

        return {'table': 'smurf_detections', 'deleted_count': deleted_count}

    async def _cleanup_old_ranks(self, cutoff_date: datetime, dry_run: bool, batch_size: int) -> Dict[str, Any]:
        """Clean up old rank records."""
        query = delete(PlayerRank).where(PlayerRank.created_at < cutoff_date)

        if dry_run:
            result = await self.db.execute(
                select(func.count(PlayerRank.id)).where(PlayerRank.created_at < cutoff_date)
            )
            count = result.scalar() or 0
            return {'table': 'player_ranks', 'would_delete': count, 'deleted_count': 0}

        result = await self.db.execute(query)
        deleted_count = result.rowcount
        await self.db.commit()

        return {'table': 'player_ranks', 'deleted_count': deleted_count}

    async def _cleanup_inactive_players(self, cutoff_date: datetime, dry_run: bool, batch_size: int) -> Dict[str, Any]:
        """Clean up inactive player records."""
        # Find players with no recent activity and no match data
        subquery = select(MatchParticipant.puuid).distinct()

        query = delete(Player).where(
            and_(
                Player.last_seen < cutoff_date,
                ~Player.puuid.in_(subquery)
            )
        )

        if dry_run:
            result = await self.db.execute(
                select(func.count(Player.puuid)).where(
                    and_(
                        Player.last_seen < cutoff_date,
                        ~Player.puuid.in_(subquery)
                    )
                )
            )
            count = result.scalar() or 0
            return {'table': 'players', 'would_delete': count, 'deleted_count': 0}

        result = await self.db.execute(query)
        deleted_count = result.rowcount
        await self.db.commit()

        return {'table': 'players', 'deleted_count': deleted_count}

    async def _cleanup_orphaned_participants(self, dry_run: bool, batch_size: int) -> Dict[str, Any]:
        """Clean up orphaned match participants."""
        subquery = select(Match.match_id)
        query = delete(MatchParticipant).where(~MatchParticipant.match_id.in_(subquery))

        if dry_run:
            result = await self.db.execute(
                select(func.count(MatchParticipant.match_id)).where(~MatchParticipant.match_id.in_(subquery))
            )
            count = result.scalar() or 0
            return {'table': 'match_participants', 'would_delete': count, 'deleted_count': 0}

        result = await self.db.execute(query)
        deleted_count = result.rowcount
        await self.db.commit()

        return {'table': 'match_participants', 'deleted_count': deleted_count}

    async def _cleanup_orphaned_ranks(self, dry_run: bool, batch_size: int) -> Dict[str, Any]:
        """Clean up orphaned rank records."""
        subquery = select(Player.puuid)
        query = delete(PlayerRank).where(~PlayerRank.puuid.in_(subquery))

        if dry_run:
            result = await self.db.execute(
                select(func.count(PlayerRank.id)).where(~PlayerRank.puuid.in_(subquery))
            )
            count = result.scalar() or 0
            return {'table': 'player_ranks', 'would_delete': count, 'deleted_count': 0}

        result = await self.db.execute(query)
        deleted_count = result.rowcount
        await self.db.commit()

        return {'table': 'player_ranks', 'deleted_count': deleted_count}

    async def _cleanup_orphaned_players(self, dry_run: bool, batch_size: int) -> Dict[str, Any]:
        """Clean up players with no related data."""
        # Players with no matches, no ranks, and no detections
        matches_subquery = select(MatchParticipant.puuid).distinct()
        ranks_subquery = select(PlayerRank.puuid).distinct()
        detections_subquery = select(SmurfDetection.puuid).distinct()

        query = delete(Player).where(
            and_(
                ~Player.puuid.in_(matches_subquery),
                ~Player.puuid.in_(ranks_subquery),
                ~Player.puuid.in_(detections_subquery),
                Player.last_seen < datetime.now() - timedelta(days=365)  # Older than 1 year
            )
        )

        if dry_run:
            result = await self.db.execute(
                select(func.count(Player.puuid)).where(
                    and_(
                        ~Player.puuid.in_(matches_subquery),
                        ~Player.puuid.in_(ranks_subquery),
                        ~Player.puuid.in_(detections_subquery),
                        Player.last_seen < datetime.now() - timedelta(days=365)
                    )
                )
            )
            count = result.scalar() or 0
            return {'table': 'players', 'would_delete': count, 'deleted_count': 0}

        result = await self.db.execute(query)
        deleted_count = result.rowcount
        await self.db.commit()

        return {'table': 'players', 'deleted_count': deleted_count}

    async def _update_table_statistics(self) -> Dict[str, Any]:
        """Update table statistics."""
        try:
            # This is a simplified implementation
            # In a real database, you would run ANALYZE commands
            tables = ['players', 'matches', 'match_participants', 'player_ranks', 'smurf_detections']
            results = {}

            for table in tables:
                try:
                    # Execute analyze query
                    await self.db.execute(f"ANALYZE {table}")
                    results[table] = 'success'
                except Exception as e:
                    results[table] = f'error: {str(e)}'

            return {'tables': results}

        except Exception as e:
            logger.error("Failed to update table statistics", error=str(e))
            return {'error': str(e)}

    async def _vacuum_tables(self) -> Dict[str, Any]:
        """Vacuum tables to reclaim space."""
        try:
            # This is a simplified implementation
            # In PostgreSQL, you would run VACUUM commands
            tables = ['players', 'matches', 'match_participants', 'player_ranks', 'smurf_detections']
            results = {}

            for table in tables:
                try:
                    # Execute vacuum query (simplified)
                    await self.db.execute(f"VACUUM {table}")
                    results[table] = 'success'
                except Exception as e:
                    results[table] = f'error: {str(e)}'

            return {'tables': results}

        except Exception as e:
            logger.error("Failed to vacuum tables", error=str(e))
            return {'error': str(e)}

    async def _analyze_tables(self) -> Dict[str, Any]:
        """Analyze tables for query optimization."""
        try:
            # Similar to _update_table_statistics but more comprehensive
            tables = ['players', 'matches', 'match_participants', 'player_ranks', 'smurf_detections']
            results = {}

            for table in tables:
                try:
                    await self.db.execute(f"ANALYZE {table}")
                    results[table] = 'success'
                except Exception as e:
                    results[table] = f'error: {str(e)}'

            return {'tables': results}

        except Exception as e:
            logger.error("Failed to analyze tables", error=str(e))
            return {'error': str(e)}

    async def _deduplicate_matches(self, dry_run: bool) -> Dict[str, Any]:
        """Remove duplicate match records."""
        # Find duplicates by match_id
        query = select(
            Match.match_id,
            func.count(Match.id).label('count')
        ).group_by(Match.match_id).having(func.count(Match.id) > 1)

        result = await self.db.execute(query)
        duplicates = result.fetchall()

        if dry_run:
            return {'table': 'matches', 'duplicate_groups': len(duplicates), 'would_delete': len(duplicates), 'deleted_count': 0}

        deleted_count = 0
        for match_id, count in duplicates:
            # Keep the newest record, delete older ones
            delete_query = delete(Match).where(
                and_(
                    Match.match_id == match_id,
                    Match.id != select(func.max(Match.id)).where(Match.match_id == match_id).scalar_subquery()
                )
            )
            result = await self.db.execute(delete_query)
            deleted_count += result.rowcount

        await self.db.commit()
        return {'table': 'matches', 'duplicate_groups': len(duplicates), 'deleted_count': deleted_count}

    async def _deduplicate_players(self, dry_run: bool) -> Dict[str, Any]:
        """Remove duplicate player records."""
        # Find duplicates by puuid
        query = select(
            Player.puuid,
            func.count(Player.puuid).label('count')
        ).group_by(Player.puuid).having(func.count(Player.puuid) > 1)

        result = await self.db.execute(query)
        duplicates = result.fetchall()

        if dry_run:
            return {'table': 'players', 'duplicate_groups': len(duplicates), 'would_delete': len(duplicates), 'deleted_count': 0}

        deleted_count = 0
        for puuid, count in duplicates:
            # Keep the record with most recent last_seen
            delete_query = delete(Player).where(
                and_(
                    Player.puuid == puuid,
                    Player.id != select(func.max(Player.id)).where(Player.puuid == puuid).scalar_subquery()
                )
            )
            result = await self.db.execute(delete_query)
            deleted_count += result.rowcount

        await self.db.commit()
        return {'table': 'players', 'duplicate_groups': len(duplicates), 'deleted_count': deleted_count}

    async def _deduplicate_detections(self, dry_run: bool) -> Dict[str, Any]:
        """Remove duplicate detection records."""
        # Find recent duplicates for the same player
        cutoff_date = datetime.now() - timedelta(days=1)
        query = select(
            SmurfDetection.puuid,
            func.count(SmurfDetection.id).label('count')
        ).where(
            SmurfDetection.last_analysis >= cutoff_date
        ).group_by(SmurfDetection.puuid).having(func.count(SmurfDetection.id) > 1)

        result = await self.db.execute(query)
        duplicates = result.fetchall()

        if dry_run:
            return {'table': 'smurf_detections', 'duplicate_groups': len(duplicates), 'would_delete': len(duplicates), 'deleted_count': 0}

        deleted_count = 0
        for puuid, count in duplicates:
            # Keep the most recent detection
            delete_query = delete(SmurfDetection).where(
                and_(
                    SmurfDetection.puuid == puuid,
                    SmurfDetection.last_analysis >= cutoff_date,
                    SmurfDetection.id != select(func.max(SmurfDetection.id)).where(
                        and_(
                            SmurfDetection.puuid == puuid,
                            SmurfDetection.last_analysis >= cutoff_date
                        )
                    ).scalar_subquery()
                )
            )
            result = await self.db.execute(delete_query)
            deleted_count += result.rowcount

        await self.db.commit()
        return {'table': 'smurf_detections', 'duplicate_groups': len(duplicates), 'deleted_count': deleted_count}