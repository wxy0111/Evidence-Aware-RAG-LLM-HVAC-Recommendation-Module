import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from .action_schema import ProposalSchema
from .paths import DEFAULT_HISTORY_PATH


@dataclass
class HistoricalCase:
    timestamp: str
    hour: int
    indoor_temp: float
    outdoor_temp: float
    optimal_temp: float
    expected_saving_percent: float
    temp_change: float
    optimization_type: str
    score: float


class HistoricalCaseRetriever:
    def __init__(self, csv_path: str | None = None):
        if csv_path is None:
            csv_path = str(DEFAULT_HISTORY_PATH)
        self.csv_path = csv_path
        self.rows = self._load_rows()

    def _load_rows(self) -> List[Dict[str, Any]]:
        path = Path(self.csv_path)
        if not path.exists():
            return []
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))

    def retrieve(self, proposal: ProposalSchema, top_k: int = 3) -> List[HistoricalCase]:
        try:
            target_dt = datetime.fromisoformat(str(proposal.timestamp).replace('Z', ''))
            target_hour = target_dt.hour
        except Exception:
            target_hour = 12

        target_optimal_temp = float(proposal.set_temperature_c)
        target_expected_saving = float(proposal.expected_saving_percent)
        target_indoor = float(proposal.metadata.get('indoor_temp', target_optimal_temp))
        target_outdoor = float(proposal.metadata.get('outdoor_temp', target_optimal_temp))

        candidates: List[HistoricalCase] = []
        for row in self.rows:
            try:
                row_dt = datetime.fromisoformat(str(row['timestamp']).replace(' ', 'T'))
                row_hour = row_dt.hour
                indoor_temp = float(row.get('indoor_temp', row.get('current_temp', target_indoor)) or target_indoor)
                outdoor_temp = float(row.get('outdoor_temp', target_outdoor) or target_outdoor)
                optimal_temp = float(row.get('optimal_temp', target_optimal_temp) or target_optimal_temp)
                original_pred = float(row.get('original_predicted_energy', 0.0) or 0.0)
                optimized_energy = float(row.get('optimized_energy', 0.0) or 0.0)
                if original_pred > 0:
                    expected_saving_percent = max(0.0, (original_pred - optimized_energy) / original_pred * 100.0)
                else:
                    expected_saving_percent = 0.0
                temp_change = float(row.get('temp_change', 0.0) or 0.0)
                optimization_type = str(row.get('optimization_type', ''))
            except Exception:
                continue

            hour_gap = abs(row_hour - target_hour)
            indoor_gap = abs(indoor_temp - target_indoor)
            outdoor_gap = abs(outdoor_temp - target_outdoor)
            optimal_gap = abs(optimal_temp - target_optimal_temp)
            saving_gap = abs(expected_saving_percent - target_expected_saving)

            score = (
                hour_gap * 1.6
                + indoor_gap * 2.0
                + outdoor_gap * 1.2
                + optimal_gap * 2.0
                + saving_gap * 0.15
            )

            candidates.append(HistoricalCase(
                timestamp=row.get('timestamp', ''),
                hour=row_hour,
                indoor_temp=indoor_temp,
                outdoor_temp=outdoor_temp,
                optimal_temp=optimal_temp,
                expected_saving_percent=expected_saving_percent,
                temp_change=temp_change,
                optimization_type=optimization_type,
                score=score,
            ))

        candidates.sort(key=lambda x: x.score)
        return candidates[:top_k]

    @staticmethod
    def summarize(cases: List[HistoricalCase]) -> Dict[str, Any]:
        if not cases:
            return {
                'count': 0,
                'avg_saving_percent': 0.0,
                'avg_indoor_temp': 0.0,
                'avg_outdoor_temp': 0.0,
                'avg_optimal_temp': 0.0,
            }
        n = len(cases)
        return {
            'count': n,
            'avg_saving_percent': sum(c.expected_saving_percent for c in cases) / n,
            'avg_indoor_temp': sum(c.indoor_temp for c in cases) / n,
            'avg_outdoor_temp': sum(c.outdoor_temp for c in cases) / n,
            'avg_optimal_temp': sum(c.optimal_temp for c in cases) / n,
        }

    @staticmethod
    def format_context(cases: List[HistoricalCase]) -> str:
        if not cases:
            return '類似履歴なし'
        lines = []
        for i, c in enumerate(cases, 1):
            lines.append(
                f"{i}. {c.timestamp} 頃, 室内 {c.indoor_temp:.1f}°C, 外気 {c.outdoor_temp:.1f}°C, 設定 {c.optimal_temp:.1f}°C, 想定節電率 {c.expected_saving_percent:.1f}%"
            )
        return '\n'.join(lines)
