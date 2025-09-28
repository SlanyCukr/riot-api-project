"""
Smurf detection specific background tasks.

Provides specialized tasks for smurf detection algorithms,
model training, and detection optimization.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
import structlog

from ..services.detection import SmurfDetectionService
from ..models.players import Player
from ..models.smurf_detection import SmurfDetection
from ..models.ranks import PlayerRank
from ..schemas.detection import DetectionRequest
from ..tasks.queue import BackgroundTask

logger = structlog.get_logger(__name__)


class DetectionTasks:
    """Specialized tasks for smurf detection and model optimization."""

    def __init__(self, detection_service: SmurfDetectionService):
        """
        Initialize detection tasks.

        Args:
            detection_service: Smurf detection service
        """
        self.detection_service = detection_service

    async def optimize_detection_thresholds(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize detection thresholds based on historical data.

        Args:
            task_data: Task data containing optimization parameters

        Returns:
            Dictionary with optimization results
        """
        sample_size = task_data.get('sample_size', 1000)
        min_confidence = task_data.get('min_confidence', 0.8)

        logger.info("Optimizing detection thresholds", sample_size=sample_size)

        try:
            # Get recent detection results for analysis
            cutoff_date = datetime.now() - timedelta(days=30)
            query = select(SmurfDetection).where(
                and_(
                    SmurfDetection.last_analysis >= cutoff_date,
                    SmurfDetection.games_analyzed >= 20,
                    SmurfDetection.confidence.in_(['high', 'medium'])
                )
            ).order_by(desc(SmurfDetection.last_analysis)).limit(sample_size)

            result = await self.detection_service.db.execute(query)
            detections = result.scalars().all()

            if len(detections) < 100:
                logger.warning("Insufficient data for threshold optimization", available=len(detections))
                return {
                    'sample_size': len(detections),
                    'optimization_performed': False,
                    'reason': 'Insufficient data',
                    'timestamp': datetime.now().isoformat()
                }

            # Analyze distribution of detection scores
            smurf_scores = [d.smurf_score for d in detections if d.is_smurf]
            non_smurf_scores = [d.smurf_score for d in detections if not d.is_smurf]

            # Calculate optimal thresholds (simplified approach)
            if smurf_scores and non_smurf_scores:
                avg_smurf_score = sum(smurf_scores) / len(smurf_scores)
                avg_non_smurf_score = sum(non_smurf_scores) / len(non_smurf_scores)

                # Suggest new thresholds
                suggested_thresholds = {
                    'detection_score_low': max(0.3, avg_non_smurf_score + 0.1),
                    'detection_score_medium': max(0.5, (avg_smurf_score + avg_non_smurf_score) / 2),
                    'detection_score_high': max(0.7, avg_smurf_score - 0.1)
                }

                logger.info(
                    "Threshold optimization completed",
                    sample_size=len(detections),
                    suggested_thresholds=suggested_thresholds
                )

                return {
                    'sample_size': len(detections),
                    'optimization_performed': True,
                    'avg_smurf_score': avg_smurf_score,
                    'avg_non_smurf_score': avg_non_smurf_score,
                    'suggested_thresholds': suggested_thresholds,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.warning("Cannot optimize thresholds - missing data categories")
                return {
                    'sample_size': len(detections),
                    'optimization_performed': False,
                    'reason': 'Missing smurf or non-smurf data',
                    'timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error("Failed to optimize detection thresholds", error=str(e))
            raise

    async def validate_detection_accuracy(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate detection accuracy by comparing recent analyses.

        Args:
            task_data: Task data containing validation parameters

        Returns:
            Dictionary with validation results
        """
        days_back = task_data.get('days_back', 7)
        min_games = task_data.get('min_games', 30)
        sample_size = task_data.get('sample_size', 100)

        logger.info("Validating detection accuracy", days_back=days_back, sample_size=sample_size)

        try:
            # Get players with multiple recent analyses
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Find players with at least 2 analyses in the period
            subquery = select(
                SmurfDetection.puuid,
                func.count(SmurfDetection.id).label('analysis_count')
            ).where(
                and_(
                    SmurfDetection.last_analysis >= cutoff_date,
                    SmurfDetection.games_analyzed >= min_games
                )
            ).group_by(SmurfDetection.puuid).having(
                func.count(SmurfDetection.id) >= 2
            )

            # Get actual detection records
            query = select(SmurfDetection).where(
                SmurfDetection.puuid.in_(select(subquery.c.puuid))
            ).order_by(SmurfDetection.puuid, SmurfDetection.last_analysis.desc())

            result = await self.detection_service.db.execute(query)
            all_detections = result.scalars().all()

            # Group by player and analyze consistency
            player_detections = {}
            for detection in all_detections:
                puuid = str(detection.puuid)
                if puuid not in player_detections:
                    player_detections[puuid] = []
                player_detections[puuid].append(detection)

            # Analyze consistency
            consistent_detections = 0
            inconsistent_detections = 0
            total_players = len(player_detections)

            for puuid, detections in player_detections.items():
                if len(detections) >= 2:
                    latest = detections[0]
                    others = detections[1:]

                    # Check if latest detection is consistent with previous ones
                    is_consistent = True
                    for prev in others:
                        if (latest.is_smurf != prev.is_smurf or
                            abs(latest.smurf_score - prev.smurf_score) > 0.2):
                            is_consistent = False
                            break

                    if is_consistent:
                        consistent_detections += 1
                    else:
                        inconsistent_detections += 1

                if total_players >= sample_size:
                    break

            consistency_rate = consistent_detections / max(consistent_detections + inconsistent_detections, 1)

            logger.info(
                "Detection accuracy validation completed",
                total_players=total_players,
                consistent_detections=consistent_detections,
                inconsistent_detections=inconsistent_detections,
                consistency_rate=consistency_rate
            )

            return {
                'total_players': total_players,
                'consistent_detections': consistent_detections,
                'inconsistent_detections': inconsistent_detections,
                'consistency_rate': consistency_rate,
                'days_back': days_back,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to validate detection accuracy", error=str(e))
            raise

    async def detect_detection_patterns(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect patterns in smurf detection results.

        Args:
            task_data: Task data containing pattern detection parameters

        Returns:
            Dictionary with pattern detection results
        """
        days_back = task_data.get('days_back', 30)
        min_detections = task_data.get('min_detections', 50)

        logger.info("Detecting smurf detection patterns", days_back=days_back)

        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Get all recent detections
            query = select(SmurfDetection).where(
                and_(
                    SmurfDetection.last_analysis >= cutoff_date,
                    SmurfDetection.games_analyzed >= 20
                )
            )

            result = await self.detection_service.db.execute(query)
            detections = result.scalars().all()

            if len(detections) < min_detections:
                logger.warning("Insufficient detections for pattern analysis")
                return {
                    'total_detections': len(detections),
                    'patterns_found': [],
                    'timestamp': datetime.now().isoformat()
                }

            # Analyze patterns
            patterns = {}

            # Confidence level distribution
            confidence_dist = {}
            for detection in detections:
                confidence = detection.confidence or 'none'
                confidence_dist[confidence] = confidence_dist.get(confidence, 0) + 1
            patterns['confidence_distribution'] = confidence_dist

            # Detection score distribution
            score_ranges = {
                '0.0-0.2': 0, '0.2-0.4': 0, '0.4-0.6': 0,
                '0.6-0.8': 0, '0.8-1.0': 0
            }
            for detection in detections:
                score = detection.smurf_score
                if score < 0.2:
                    score_ranges['0.0-0.2'] += 1
                elif score < 0.4:
                    score_ranges['0.2-0.4'] += 1
                elif score < 0.6:
                    score_ranges['0.4-0.6'] += 1
                elif score < 0.8:
                    score_ranges['0.6-0.8'] += 1
                else:
                    score_ranges['0.8-1.0'] += 1
            patterns['score_distribution'] = score_ranges

            # Account level analysis
            account_levels = {}
            for detection in detections:
                level = detection.account_level or 0
                if level < 50:
                    account_levels['low'] = account_levels.get('low', 0) + 1
                elif level < 100:
                    account_levels['medium'] = account_levels.get('medium', 0) + 1
                else:
                    account_levels['high'] = account_levels.get('high', 0) + 1
            patterns['account_level_distribution'] = account_levels

            # Win rate analysis for detected smurfs
            smurf_win_rates = [d.win_rate_score for d in detections if d.is_smurf and d.win_rate_score]
            if smurf_win_rates:
                patterns['smurf_avg_win_rate'] = sum(smurf_win_rates) / len(smurf_win_rates)
                patterns['smurf_win_rate_range'] = {
                    'min': min(smurf_win_rates),
                    'max': max(smurf_win_rates)
                }

            logger.info(
                "Pattern detection completed",
                total_detections=len(detections),
                patterns_analyzed=len(patterns)
            )

            return {
                'total_detections': len(detections),
                'patterns': patterns,
                'days_back': days_back,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to detect detection patterns", error=str(e))
            raise

    async def generate_detection_report(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive smurf detection report.

        Args:
            task_data: Task data containing report parameters

        Returns:
            Dictionary with report results
        """
        days_back = task_data.get('days_back', 7)
        include_details = task_data.get('include_details', True)

        logger.info("Generating detection report", days_back=days_back)

        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Get basic statistics
            total_query = select(func.count(SmurfDetection.id)).where(
                SmurfDetection.last_analysis >= cutoff_date
            )
            total_result = await self.detection_service.db.execute(total_query)
            total_detections = total_result.scalar() or 0

            smurf_query = select(func.count(SmurfDetection.id)).where(
                and_(
                    SmurfDetection.last_analysis >= cutoff_date,
                    SmurfDetection.is_smurf == True
                )
            )
            smurf_result = await self.detection_service.db.execute(smurf_query)
            smurf_count = smurf_result.scalar() or 0

            # Calculate detection rate
            detection_rate = smurf_count / max(total_detections, 1)

            # Get confidence distribution
            confidence_query = select(
                SmurfDetection.confidence,
                func.count(SmurfDetection.id)
            ).where(
                SmurfDetection.last_analysis >= cutoff_date
            ).group_by(SmurfDetection.confidence)

            confidence_result = await self.detection_service.db.execute(confidence_query)
            confidence_dist = {str(row[0] or 'none'): row[1] for row in confidence_result}

            # Get high confidence smurfs
            high_confidence_query = select(SmurfDetection).where(
                and_(
                    SmurfDetection.last_analysis >= cutoff_date,
                    SmurfDetection.is_smurf == True,
                    SmurfDetection.confidence == 'high'
                )
            ).limit(10)

            high_confidence_result = await self.detection_service.db.execute(high_confidence_query)
            high_confidence_smurfs = high_confidence_result.scalars().all()

            report = {
                'period_days': days_back,
                'total_detections': total_detections,
                'smurf_count': smurf_count,
                'detection_rate': detection_rate,
                'confidence_distribution': confidence_dist,
                'high_confidence_smurfs_count': len(high_confidence_smurfs),
                'generated_at': datetime.now().isoformat()
            }

            if include_details:
                report['high_confidence_smurfs'] = [
                    {
                        'puuid': str(d.puuid),
                        'detection_score': float(d.smurf_score),
                        'confidence': d.confidence,
                        'games_analyzed': d.games_analyzed,
                        'analysis_date': d.last_analysis.isoformat()
                    }
                    for d in high_confidence_smurfs
                ]

            logger.info(
                "Detection report generated",
                total_detections=total_detections,
                smurf_count=smurf_count,
                detection_rate=detection_rate
            )

            return report

        except Exception as e:
            logger.error("Failed to generate detection report", error=str(e))
            raise

    async def calibrate_detection_model(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calibrate detection model based on feedback and performance.

        Args:
            task_data: Task data containing calibration parameters

        Returns:
            Dictionary with calibration results
        """
        sample_size = task_data.get('sample_size', 500)
        calibration_method = task_data.get('calibration_method', 'statistical')

        logger.info("Calibrating detection model", method=calibration_method)

        try:
            # Get recent detection results for calibration
            cutoff_date = datetime.now() - timedelta(days=60)
            query = select(SmurfDetection).where(
                and_(
                    SmurfDetection.last_analysis >= cutoff_date,
                    SmurfDetection.games_analyzed >= 25,
                    SmurfDetection.confidence.in_(['high', 'medium'])
                )
            ).order_by(desc(SmurfDetection.last_analysis)).limit(sample_size)

            result = await self.detection_service.db.execute(query)
            detections = result.scalars().all()

            if len(detections) < 100:
                logger.warning("Insufficient data for model calibration")
                return {
                    'sample_size': len(detections),
                    'calibration_performed': False,
                    'reason': 'Insufficient data',
                    'timestamp': datetime.now().isoformat()
                }

            # Analyze current model performance
            smurf_detections = [d for d in detections if d.is_smurf]
            non_smurf_detections = [d for d in detections if not d.is_smurf]

            if calibration_method == 'statistical':
                # Statistical calibration
                calibration_results = await self._statistical_calibration(
                    smurf_detections, non_smurf_detections
                )
            else:
                # Simple calibration
                calibration_results = await self._simple_calibration(
                    smurf_detections, non_smurf_detections
                )

            logger.info(
                "Detection model calibration completed",
                sample_size=len(detections),
                calibration_method=calibration_method
            )

            return {
                'sample_size': len(detections),
                'calibration_performed': True,
                'calibration_method': calibration_method,
                'calibration_results': calibration_results,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("Failed to calibrate detection model", error=str(e))
            raise

    async def _statistical_calibration(
        self,
        smurf_detections: List[SmurfDetection],
        non_smurf_detections: List[SmurfDetection]
    ) -> Dict[str, Any]:
        """Perform statistical calibration of detection model."""
        # Calculate means and standard deviations
        smurf_scores = [d.smurf_score for d in smurf_detections]
        non_smurf_scores = [d.smurf_score for d in non_smurf_detections]

        if not smurf_scores or not non_smurf_scores:
            return {'error': 'Insufficient data for statistical calibration'}

        import statistics
        smurf_mean = statistics.mean(smurf_scores)
        smurf_stdev = statistics.stdev(smurf_scores) if len(smurf_scores) > 1 else 0
        non_smurf_mean = statistics.mean(non_smurf_scores)
        non_smurf_stdev = statistics.stdev(non_smurf_scores) if len(non_smurf_scores) > 1 else 0

        # Calculate optimal separation point
        optimal_threshold = (smurf_mean + non_smurf_mean) / 2

        return {
            'smurf_stats': {'mean': smurf_mean, 'stdev': smurf_stdev},
            'non_smurf_stats': {'mean': non_smurf_mean, 'stdev': non_smurf_stdev},
            'optimal_threshold': optimal_threshold,
            'separation_quality': abs(smurf_mean - non_smurf_mean) / max(smurf_stdev + non_smurf_stdev, 0.001)
        }

    async def _simple_calibration(
        self,
        smurf_detections: List[SmurfDetection],
        non_smurf_detections: List[SmurfDetection]
    ) -> Dict[str, Any]:
        """Perform simple calibration of detection model."""
        smurf_scores = [d.smurf_score for d in smurf_detections]
        non_smurf_scores = [d.smurf_score for d in non_smurf_detections]

        if not smurf_scores or not non_smurf_scores:
            return {'error': 'Insufficient data for simple calibration'}

        # Simple threshold adjustment
        min_smurf_score = min(smurf_scores)
        max_non_smurf_score = max(non_smurf_scores)

        suggested_threshold = (min_smurf_score + max_non_smurf_score) / 2

        return {
            'min_smurf_score': min_smurf_score,
            'max_non_smurf_score': max_non_smurf_score,
            'suggested_threshold': suggested_threshold,
            'overlap_exists': min_smurf_score <= max_non_smurf_score
        }