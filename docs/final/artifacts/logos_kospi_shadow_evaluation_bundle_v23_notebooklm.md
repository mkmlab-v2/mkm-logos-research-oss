# logos_kospi_shadow_evaluation_bundle_v23 (JSON mirror for NotebookLM)

**SSOT**: `reports/research/logos_shadow_v1/logos_kospi_shadow_evaluation_bundle_v23_latest.json` — 아래 fenced JSON은 동일 내용을 NotebookLM 파일 소스용으로 복제한 것이다.

```json
{
  "schema": "logos_kospi_shadow_evaluation_bundle_v23",
  "ts_utc": "2026-04-03T15:25:22Z",
  "precision_definition": "precrash_zone_precision (v21)",
  "cost_formula": "avg_precrash_zone_precision / (1 + load_coeff*avg_load_ratio + false_coeff*avg_false_alert_density)",
  "coefficients": {
    "load": 4.8,
    "false_alert_density": 1.5
  },
  "min_cost_efficiency_score": 0.35,
  "extra_args": [
    "--cluster-merge-days",
    "10",
    "--refractory-days",
    "10",
    "--enable-recent-precision-layer",
    "--recent-precision-min-evidence",
    "3",
    "--recent-precision-density-window",
    "30",
    "--recent-precision-density-max",
    "1"
  ],
  "temporal": {
    "windows": [
      [
        "t1_2003_2007_pre_gfc",
        "2003-01-01",
        "2007-12-31"
      ],
      [
        "t2_2010_2014_post_gfc",
        "2010-01-01",
        "2014-12-31"
      ],
      [
        "t3_2023_2024_recent",
        "2023-01-01",
        "2024-12-31"
      ]
    ],
    "per_window": [
      {
        "window": "t1_2003_2007_pre_gfc",
        "period": [
          "2003-01-01",
          "2007-12-31"
        ],
        "rows": 492,
        "metrics": {
          "hit_direction_rate": 0.333333,
          "warning_precision": 0.333333,
          "precrash_zone_precision": 0.333333,
          "precrash_zone_true_count": 2,
          "warning_false_positive_ratio": 0.666667,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 0.25,
          "warnings_count": 6,
          "warning_load_ratio": 0.012195,
          "false_alert_count": 4,
          "false_alert_density": 0.00813,
          "crash_event_count": 8,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.388101,
          "mean_cycle_resonance": 0.713636,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "t2_2010_2014_post_gfc",
        "period": [
          "2010-01-01",
          "2014-12-31"
        ],
        "rows": 1238,
        "metrics": {
          "hit_direction_rate": 0.423077,
          "warning_precision": 0.076923,
          "precrash_zone_precision": 0.076923,
          "precrash_zone_true_count": 2,
          "warning_false_positive_ratio": 0.923077,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 0.272727,
          "warnings_count": 26,
          "warning_load_ratio": 0.021002,
          "false_alert_count": 24,
          "false_alert_density": 0.019386,
          "crash_event_count": 11,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.11416,
          "mean_cycle_resonance": 0.254196,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "t3_2023_2024_recent",
        "period": [
          "2023-01-01",
          "2024-12-31"
        ],
        "rows": 489,
        "metrics": {
          "hit_direction_rate": 0.0,
          "warning_precision": 0.0,
          "precrash_zone_precision": 0.0,
          "precrash_zone_true_count": 0,
          "warning_false_positive_ratio": 1.0,
          "recent_era_warnings_count": 2,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 0.0,
          "warnings_count": 2,
          "warning_load_ratio": 0.00409,
          "false_alert_count": 2,
          "false_alert_density": 0.00409,
          "crash_event_count": 3,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.463382,
          "mean_cycle_resonance": 0.693182,
          "confidence_from_lens": 0.2
        }
      }
    ],
    "aggregate": {
      "avg_crash_warning_recall": 0.174242,
      "avg_precrash_zone_precision": 0.136752,
      "avg_hit_direction_rate": 0.252137,
      "avg_warning_load_ratio": 0.012429,
      "avg_false_alert_density": 0.010535,
      "cost_efficiency_score": 0.127156,
      "pass_cost_gate": false
    }
  },
  "holdout": {
    "windows": [
      [
        "h1_2011_euro_daily",
        "2011-07-01",
        "2012-01-31"
      ],
      [
        "h2_2015_cn_deval_daily",
        "2015-06-01",
        "2016-02-29"
      ],
      [
        "h3_2018_q4_riskoff_daily",
        "2018-08-01",
        "2019-01-31"
      ],
      [
        "h4_2022_rate_shock_daily",
        "2022-01-01",
        "2022-12-31"
      ]
    ],
    "per_window": [
      {
        "window": "h1_2011_euro_daily",
        "period": [
          "2011-07-01",
          "2012-01-31"
        ],
        "rows": 145,
        "metrics": {
          "hit_direction_rate": 0.5,
          "warning_precision": 1.0,
          "precrash_zone_precision": 1.0,
          "precrash_zone_true_count": 2,
          "warning_false_positive_ratio": 0.0,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 0.666667,
          "warnings_count": 2,
          "warning_load_ratio": 0.013793,
          "false_alert_count": 0,
          "false_alert_density": 0.0,
          "crash_event_count": 6,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.150406,
          "mean_cycle_resonance": 0.202273,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "h2_2015_cn_deval_daily",
        "period": [
          "2015-06-01",
          "2016-02-29"
        ],
        "rows": 186,
        "metrics": {
          "hit_direction_rate": 0.25,
          "warning_precision": 0.25,
          "precrash_zone_precision": 0.25,
          "precrash_zone_true_count": 1,
          "warning_false_positive_ratio": 0.75,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 1.0,
          "warnings_count": 4,
          "warning_load_ratio": 0.021505,
          "false_alert_count": 3,
          "false_alert_density": 0.016129,
          "crash_event_count": 1,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.273328,
          "mean_cycle_resonance": 0.478409,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "h3_2018_q4_riskoff_daily",
        "period": [
          "2018-08-01",
          "2019-01-31"
        ],
        "rows": 123,
        "metrics": {
          "hit_direction_rate": 0.666667,
          "warning_precision": 0.333333,
          "precrash_zone_precision": 0.333333,
          "precrash_zone_true_count": 1,
          "warning_false_positive_ratio": 0.666667,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 1.0,
          "warnings_count": 3,
          "warning_load_ratio": 0.02439,
          "false_alert_count": 2,
          "false_alert_density": 0.01626,
          "crash_event_count": 2,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.21088,
          "mean_cycle_resonance": 0.468182,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "h4_2022_rate_shock_daily",
        "period": [
          "2022-01-01",
          "2022-12-31"
        ],
        "rows": 244,
        "metrics": {
          "hit_direction_rate": 0.5,
          "warning_precision": 1.0,
          "precrash_zone_precision": 1.0,
          "precrash_zone_true_count": 2,
          "warning_false_positive_ratio": 0.0,
          "recent_era_warnings_count": 2,
          "recent_era_precrash_zone_precision": 1.0,
          "crash_warning_recall": 0.375,
          "warnings_count": 2,
          "warning_load_ratio": 0.008197,
          "false_alert_count": 0,
          "false_alert_density": 0.0,
          "crash_event_count": 8,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.48924,
          "mean_cycle_resonance": 0.754545,
          "confidence_from_lens": 0.2
        }
      }
    ],
    "aggregate": {
      "avg_crash_warning_recall": 0.760417,
      "avg_precrash_zone_precision": 0.645833,
      "avg_hit_direction_rate": 0.479167,
      "avg_warning_load_ratio": 0.016971,
      "avg_false_alert_density": 0.008097,
      "cost_efficiency_score": 0.590553,
      "pass_cost_gate": true
    }
  },
  "combined_all_windows": {
    "per_window": [
      {
        "window": "t1_2003_2007_pre_gfc",
        "period": [
          "2003-01-01",
          "2007-12-31"
        ],
        "rows": 492,
        "metrics": {
          "hit_direction_rate": 0.333333,
          "warning_precision": 0.333333,
          "precrash_zone_precision": 0.333333,
          "precrash_zone_true_count": 2,
          "warning_false_positive_ratio": 0.666667,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 0.25,
          "warnings_count": 6,
          "warning_load_ratio": 0.012195,
          "false_alert_count": 4,
          "false_alert_density": 0.00813,
          "crash_event_count": 8,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.388101,
          "mean_cycle_resonance": 0.713636,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "t2_2010_2014_post_gfc",
        "period": [
          "2010-01-01",
          "2014-12-31"
        ],
        "rows": 1238,
        "metrics": {
          "hit_direction_rate": 0.423077,
          "warning_precision": 0.076923,
          "precrash_zone_precision": 0.076923,
          "precrash_zone_true_count": 2,
          "warning_false_positive_ratio": 0.923077,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 0.272727,
          "warnings_count": 26,
          "warning_load_ratio": 0.021002,
          "false_alert_count": 24,
          "false_alert_density": 0.019386,
          "crash_event_count": 11,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.11416,
          "mean_cycle_resonance": 0.254196,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "t3_2023_2024_recent",
        "period": [
          "2023-01-01",
          "2024-12-31"
        ],
        "rows": 489,
        "metrics": {
          "hit_direction_rate": 0.0,
          "warning_precision": 0.0,
          "precrash_zone_precision": 0.0,
          "precrash_zone_true_count": 0,
          "warning_false_positive_ratio": 1.0,
          "recent_era_warnings_count": 2,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 0.0,
          "warnings_count": 2,
          "warning_load_ratio": 0.00409,
          "false_alert_count": 2,
          "false_alert_density": 0.00409,
          "crash_event_count": 3,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.463382,
          "mean_cycle_resonance": 0.693182,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "h1_2011_euro_daily",
        "period": [
          "2011-07-01",
          "2012-01-31"
        ],
        "rows": 145,
        "metrics": {
          "hit_direction_rate": 0.5,
          "warning_precision": 1.0,
          "precrash_zone_precision": 1.0,
          "precrash_zone_true_count": 2,
          "warning_false_positive_ratio": 0.0,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 0.666667,
          "warnings_count": 2,
          "warning_load_ratio": 0.013793,
          "false_alert_count": 0,
          "false_alert_density": 0.0,
          "crash_event_count": 6,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.150406,
          "mean_cycle_resonance": 0.202273,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "h2_2015_cn_deval_daily",
        "period": [
          "2015-06-01",
          "2016-02-29"
        ],
        "rows": 186,
        "metrics": {
          "hit_direction_rate": 0.25,
          "warning_precision": 0.25,
          "precrash_zone_precision": 0.25,
          "precrash_zone_true_count": 1,
          "warning_false_positive_ratio": 0.75,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 1.0,
          "warnings_count": 4,
          "warning_load_ratio": 0.021505,
          "false_alert_count": 3,
          "false_alert_density": 0.016129,
          "crash_event_count": 1,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.273328,
          "mean_cycle_resonance": 0.478409,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "h3_2018_q4_riskoff_daily",
        "period": [
          "2018-08-01",
          "2019-01-31"
        ],
        "rows": 123,
        "metrics": {
          "hit_direction_rate": 0.666667,
          "warning_precision": 0.333333,
          "precrash_zone_precision": 0.333333,
          "precrash_zone_true_count": 1,
          "warning_false_positive_ratio": 0.666667,
          "recent_era_warnings_count": 0,
          "recent_era_precrash_zone_precision": 0.0,
          "crash_warning_recall": 1.0,
          "warnings_count": 3,
          "warning_load_ratio": 0.02439,
          "false_alert_count": 2,
          "false_alert_density": 0.01626,
          "crash_event_count": 2,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.21088,
          "mean_cycle_resonance": 0.468182,
          "confidence_from_lens": 0.2
        }
      },
      {
        "window": "h4_2022_rate_shock_daily",
        "period": [
          "2022-01-01",
          "2022-12-31"
        ],
        "rows": 244,
        "metrics": {
          "hit_direction_rate": 0.5,
          "warning_precision": 1.0,
          "precrash_zone_precision": 1.0,
          "precrash_zone_true_count": 2,
          "warning_false_positive_ratio": 0.0,
          "recent_era_warnings_count": 2,
          "recent_era_precrash_zone_precision": 1.0,
          "crash_warning_recall": 0.375,
          "warnings_count": 2,
          "warning_load_ratio": 0.008197,
          "false_alert_count": 0,
          "false_alert_density": 0.0,
          "crash_event_count": 8,
          "direction_sign_from_lens": "neutral",
          "direction_score_from_lens": 0.0,
          "mean_composite_direction_score": 0.48924,
          "mean_cycle_resonance": 0.754545,
          "confidence_from_lens": 0.2
        }
      }
    ],
    "aggregate": {
      "avg_crash_warning_recall": 0.509199,
      "avg_precrash_zone_precision": 0.427656,
      "avg_hit_direction_rate": 0.381868,
      "avg_warning_load_ratio": 0.015025,
      "avg_false_alert_density": 0.009142,
      "cost_efficiency_score": 0.393851,
      "pass_cost_gate": true
    }
  },
  "note": "Research-only OBSERVATION_ONLY; combined uses 7 windows (3 temporal + 4 holdout)."
}
```
