"""
Player analysis background tasks for smurf detection and performance analysis.

Provides tasks for analyzing player behavior, detecting smurfs,
and generating player statistics.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import structlog

from ..services.detection import SmurfDetectionService
from ..models.players import Player
from ..models.smurf_detection import SmurfDetection
from ..models.ranks import PlayerRank
from ..schemas.detection import DetectionRequest
from ..tasks.queue import BackgroundTask

logger = structlog.get_logger(__name__)


class PlayerAnalysisTasks:
    """Background tasks for player analysis and smurf detection."""

    def __init__(self, detection_service: SmurfDetectionService):
        """
        Initialize player analysis tasks.

        Args:
            detection_service: Smurf detection service
        """
        self.detection_service = detection_service

    async def analyze_player_for_smurf(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a specific player for smurf behavior.

        Args:
            task_data: Task data containing analysis parameters

        Returns:
            Dictionary with analysis results
        """
        puuid = task_data['puuid']
        min_games = task_data.get('min_games', 30)
        queue_filter = task_data.get('queue_filter', 420)
        force_reanalyze = task_data.get('force_reanalyze', False)

        logger.info("Analyzing player for smurf behavior", puuid=puuid)

        try:
            result = await self.detection_service.analyze_player(
                puuid=puuid,
                min_games=min_games,
                queue_filter=queue_filter,
                force_reanalyze=force_reanalyze
            )

            logger.info(
                "Player analysis completed",
                puuid=puuid,
                is_smurf=result.is_smurf,
                detection_score=result.detection_score,
                confidence_level=result.confidence_level
            )

            return {
                'puuid': puuid,
                'analysis_result': result.dict(),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to analyze player", puuid=puuid, error=str(e))
            raise

    async def batch_analyze_players(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze multiple players for smurf behavior.

        Args:
            task_data: Task data containing batch parameters

        Returns:
            Dictionary with batch analysis results
        """
        player_puuids = task_data['puuids']
        batch_size = task_data.get('batch_size', 10)
        delay_between_players = task_data.get('delay_seconds', 2)
        analysis_config = task_data.get('analysis_config', {})

        logger.info("Starting batch player analysis", total_players=len(player_puuids))

        try:
            analyzed_count = 0
            smurf_count = 0
            errors = []
            detection_scores = []

            for i, puuid in enumerate(player_puuids):
                try:
                    # Prepare analysis request
                    request_data = {
                        'puuid': puuid,
                        'min_games': analysis_config.get('min_games', 30),
                        'queue_filter': analysis_config.get('queue_filter', 420),
                        'force_reanalyze': analysis_config.get('force_reanalyze', False)
                    }

                    result = await self.analyze_player_for_smurf(request_data)

                    analyzed_count += 1
                    detection_scores.append(result['analysis_result']['detection_score'])

                    if result['analysis_result']['is_smurf']:
                        smurf_count += 1

                    # Log progress
                    if (i + 1) % batch_size == 0:
                        logger.info(
                            "Batch analysis progress",
                            analyzed=analyzed_count,
                            smurfs_found=smurf_count,
                            remaining=len(player_puuids) - (i + 1)
                        )

                except Exception as e:
                    errors.append({'puuid': puuid, 'error': str(e)})
                    logger.warning("Failed to analyze player in batch", puuid=puuid, error=str(e))

                # Delay between players to respect rate limits
                if i < len(player_puuids) - 1:
                    await asyncio.sleep(delay_between_players)

            # Calculate statistics
            avg_detection_score = sum(detection_scores) / len(detection_scores) if detection_scores else 0.0

            logger.info(
                "Batch analysis completed",
                total_players=len(player_puuids),
                successfully_analyzed=analyzed_count,
                smurfs_found=smurf_count,
                avg_detection_score=avg_detection_score,
                errors=len(errors)
            )

            return {
                'total_players': len(player_puuids),
                'analyzed_count': analyzed_count,
                'smurf_count': smurf_count,
                'avg_detection_score': avg_detection_score,
                'errors': errors,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to batch analyze players", error=str(e))
            raise

    async def analyze_suspicious_players(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze players with suspicious behavior patterns.

        Args:
            task_data: Task data containing analysis parameters

        Returns:
            Dictionary with analysis results
        """
        limit = task_data.get('limit', 50)
        min_win_rate = task_data.get('min_win_rate', 0.6)  # 60% win rate
        min_games = task_data.get('min_games', 20)

        logger.info("Analyzing suspicious players", limit=limit, min_win_rate=min_win_rate)

        try:
            # Get suspicious players based on performance metrics
            suspicious_puuids = await self._get_suspicious_players(
                min_win_rate=min_win_rate,
                min_games=min_games,
                limit=limit
            )

            if not suspicious_puuids:
                logger.info("No suspicious players found")
                return {
                    'total_players': 0,
                    'analyzed_count': 0,
                    'smurf_count': 0,
                    'timestamp': datetime.now().isoformat()
                }

            # Analyze the suspicious players
            batch_result = await self.batch_analyze_players({
                'puuids': suspicious_puuids,
                'batch_size': 10,
                'delay_seconds': 3,  # Longer delay for suspicious players
                'analysis_config': {
                    'min_games': min_games,
                    'force_reanalyze': True
                }
            })

            logger.info(
                "Suspicious player analysis completed",
                total_suspicious=len(suspicious_puuids),
                smurfs_detected=batch_result['smurf_count']
            )

            return {
                'total_suspicious_players': len(suspicious_puuids),
                'analyzed_count': batch_result['analyzed_count'],
                'smurf_count': batch_result['smurf_count'],
                'avg_detection_score': batch_result['avg_detection_score'],
                'errors': batch_result['errors'],
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to analyze suspicious players", error=str(e))
            raise

    async def analyze_new_players(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze recently created players for potential smurf behavior.

        Args:
            task_data: Task data containing analysis parameters

        Returns:
            Dictionary with analysis results
        """
        days_threshold = task_data.get('days_threshold', 30)  # Players created in last 30 days
        limit = task_data.get('limit', 100)
        min_account_level = task_data.get('min_account_level', 1)

        logger.info("Analyzing new players", days_threshold=days_threshold, limit=limit)

        try:
            # Get recently created players
            cutoff_date = datetime.now() - timedelta(days=days_threshold)

            query = select(Player.puuid).where(
                and_(
                    Player.created_at >= cutoff_date,
                    Player.account_level >= min_account_level,
                    Player.puuid.isnot(None)
                )
            ).order_by(Player.created_at.desc()).limit(limit)

            result = await self.detection_service.db.execute(query)
            new_players = result.scalars().all()

            if not new_players:
                logger.info("No new players found")
                return {
                    'total_players': 0,
                    'analyzed_count': 0,
                    'smurf_count': 0,
                    'timestamp': datetime.now().isoformat()
                }

            # Analyze new players
            batch_result = await self.batch_analyze_players({
                'puuids': list(new_players),
                'batch_size': 15,
                'delay_seconds': 2,
                'analysis_config': {
                    'min_games': 20,  # Lower threshold for new players
                    'force_reanalyze': True
                }
            })

            logger.info(
                "New player analysis completed",
                total_new_players=len(new_players),
                smurfs_detected=batch_result['smurf_count']
            )

            return {
                'total_new_players': len(new_players),
                'analyzed_count': batch_result['analyzed_count'],
                'smurf_count': batch_result['smurf_count'],
                'avg_detection_score': batch_result['avg_detection_score'],
                'errors': batch_result['errors'],
                'days_threshold': days_threshold,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to analyze new players", error=str(e))
            raise

    async def reanalyze_old_detections(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reanalyze players with old detection results.

        Args:
            task_data: Task data containing reanalysis parameters

        Returns:
            Dictionary with reanalysis results
        """
        days_threshold = task_data.get('days_threshold', 30)  # Detections older than 30 days
        limit = task_data.get('limit', 100)
        only_smurfs = task_data.get('only_smurfs', True)

        logger.info("Reanalyzing old detections", days_threshold=days_threshold, limit=limit)

        try:
            # Get old detection results
            cutoff_date = datetime.now() - timedelta(days=days_threshold)

            query = select(SmurfDetection.puuid).where(
                SmurfDetection.last_analysis < cutoff_date
            )

            if only_smurfs:
                query = query.where(SmurfDetection.is_smurf == True)

            query = query.order_by(SmurfDetection.last_analysis.asc()).limit(limit)

            result = await self.detection_service.db.execute(query)
            old_detections = result.scalars().all()

            if not old_detections:
                logger.info("No old detections found for reanalysis")
                return {
                    'total_players': 0,
                    'analyzed_count': 0,
                    'changed_detections': 0,
                    'timestamp': datetime.now().isoformat()
                }

            # Reanalyze players
            puuids = [str(puuid) for puuid in old_detections]
            batch_result = await self.batch_analyze_players({
                'puuids': puuids,
                'batch_size': 10,
                'delay_seconds': 2,
                'analysis_config': {
                    'force_reanalyze': True
                }
            })

            # Check for changed detection results
            changed_detections = 0
            for puuid in puuids:
                if await self._has_detection_changed(puuid):
                    changed_detections += 1

            logger.info(
                "Old detection reanalysis completed",
                total_players=len(puuids),
                changed_detections=changed_detections
            )

            return {
                'total_players': len(puuids),
                'analyzed_count': batch_result['analyzed_count'],
                'changed_detections': changed_detections,
                'smurf_count': batch_result['smurf_count'],
                'avg_detection_score': batch_result['avg_detection_score'],
                'errors': batch_result['errors'],
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to reanalyze old detections", error=str(e))
            raise

    async def analyze_rank_jumps(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze players with unusual rank progression.

        Args:
            task_data: Task data containing analysis parameters

        Returns:
            Dictionary with analysis results
        """
        tier_threshold = task_data.get('tier_threshold', 2)  # Jumped 2+ tiers
        days_threshold = task_data.get('days_threshold', 14)  # Within last 14 days
        limit = task_data.get('limit', 50)

        logger.info("Analyzing rank jumps", tier_threshold=tier_threshold, limit=limit)

        try:
            # Get players with significant rank progression
            rank_jumpers = await self._get_rank_jumpers(
                tier_threshold=tier_threshold,
                days_threshold=days_threshold,
                limit=limit
            )

            if not rank_jumpers:
                logger.info("No players with significant rank jumps found")
                return {
                    'total_players': 0,
                    'analyzed_count': 0,
                    'smurf_count': 0,
                    'timestamp': datetime.now().isoformat()
                }

            # Analyze players with rank jumps
            puuids = [player[0] for player in rank_jumpers]
            batch_result = await self.batch_analyze_players({
                'puuids': puuids,
                'batch_size': 10,
                'delay_seconds': 3,
                'analysis_config': {
                    'force_reanalyze': True
                }
            })

            logger.info(
                "Rank jump analysis completed",
                total_players=len(puuids),
                smurfs_detected=batch_result['smurf_count']
            )

            return {
                'total_players': len(puuids),
                'analyzed_count': batch_result['analyzed_count'],
                'smurf_count': batch_result['smurf_count'],
                'avg_detection_score': batch_result['avg_detection_score'],
                'errors': batch_result['errors'],
                'tier_threshold': tier_threshold,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to analyze rank jumps", error=str(e))
            raise

    async def _get_suspicious_players(
        self,
        min_win_rate: float,
        min_games: int,
        limit: int
    ) -> List[str]:
        """Get players with suspicious performance metrics."""
        # This is a simplified implementation
        # In a real implementation, you would query player performance statistics
        query = select(Player.puuid).where(
            and_(
                Player.puuid.isnot(None),
                Player.last_seen >= datetime.now() - timedelta(days=30)
            )
        ).limit(limit)

        result = await self.detection_service.db.execute(query)
        return [str(puuid) for puuid in result.scalars().all()]

    async def _get_rank_jumpers(
        self,
        tier_threshold: int,
        days_threshold: int,
        limit: int
    ) -> List[tuple]:
        """Get players with significant rank progression."""
        # This is a simplified implementation
        # In a real implementation, you would compare current and historical rank data
        query = select(Player.puuid).where(
            and_(
                Player.puuid.isnot(None),
                Player.last_seen >= datetime.now() - timedelta(days=days_threshold)
            )
        ).limit(limit)

        result = await self.detection_service.db.execute(query)
        return [(str(puuid),) for puuid in result.scalars().all()]

    async def _has_detection_changed(self, puuid: str) -> bool:
        """Check if detection result has changed for a player."""
        # Compare last two detection results for changes
        query = select(SmurfDetection).where(
            SmurfDetection.puuid == puuid
        ).order_by(SmurfDetection.last_analysis.desc()).limit(2)

        result = await self.detection_service.db.execute(query)
        detections = result.scalars().all()

        if len(detections) < 2:
            return False

        latest = detections[0]
        previous = detections[1]

        return (
            latest.is_smurf != previous.is_smurf or
            latest.confidence != previous.confidence or
            abs(latest.smurf_score - previous.smurf_score) > 0.1
        )