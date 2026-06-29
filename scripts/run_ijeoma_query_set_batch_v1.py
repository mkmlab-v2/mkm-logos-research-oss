"""Run IJEOMA NotebookLM QUERY_SET batch via nlm CLI; write jsonl + summary."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UUID = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"
OUT_DIR = ROOT / "reports/constitution/btrack_pilot"

QUESTIONS: dict[str, list[tuple[str, str]]] = {
    "a": [
        (
            "Q01",
            "성명론에서 말하는 天機와 人事의 네 가지 항목씩을 표로 정리하고, 각각 몸의 어떤 기관·감각과 연결되는지 원문 근거를 붙여라.",
        ),
        (
            "Q02",
            "四象人 辨證論에서 네 체질의 인원 수 대략과 太陽人이 적은 이유가 어떻게 서술되는지 인용하라.",
        ),
        (
            "Q03",
            "少陰人과 少陽人의 표·里 병증 구분에서 장부·한열 논리가 어떻게 다른지 요약하라.",
        ),
        (
            "Q04",
            "太陰人과 太陽人의 체형·기질 서술을 나란히 비교하라 (원문 구절 인용).",
        ),
        (
            "Q05",
            "동의수세보원에서 張仲景 인용이 나오는 대목을 한 가지 고르고, 이제마가 그것을 어떤 사상체질 해석으로 연결하는지 설명하라.",
        ),
        (
            "Q06",
            "桂枝湯·小柴胡湯 등이 등장할 때, 어떤 체질·병증에 쓰이고 부적절하다고 지적되는 경우가 있는지 예를 들어라.",
        ),
        (
            "Q07",
            "성명론에서 驕·矜·伐·夸와 恭·敬 등 덕목·심리가 수명과 어떻게 연결되는지 한 단락으로 요약하라.",
        ),
        (
            "Q08",
            "四象人 각각의 體形氣像에서 강한 부위와 약한 부위가 어떻게 대비되는지 표로 정리하라.",
        ),
        (
            "Q09",
            "서문·일러두기에 나온 입력 계보(행림 1979, 김형태 본, 이필래 입력 등)를 한 줄로 정리하라.",
        ),
        (
            "Q10",
            "이 텍스트만으로 답이 불충분한 주제가 있다면 무엇이며, 어떤 외부 원전(격치고 등)이 필요한지 짧게 쓰라.",
        ),
    ],
    "b": [
        (
            "Q11",
            "체질 분류를 AI 파이프라인(입력 특징 → 라벨)으로 모델링할 때, 원전에서 요구하는 관찰 단위(표·里·한열 등)를 어떤 입력 스키마로 옮기면 혼선이 가장 적은지 제안하라.",
        ),
        (
            "Q12",
            "페르소나·대화 톤을 사상체질에 맞추는 설계가 있을 때, 과적합·의료 주장 오인을 막기 위한 가드레일(금지 문구·면책·상담 유도)을 원전 논리와 연결해 열거하라.",
        ),
        (
            "Q13",
            "RAG/노트북이 동의수세보원 구절을 인용할 때, 맥락 단절(한 구절만 인용) 위험을 줄이기 위한 질문 템플릿 3가지를 제시하라.",
        ),
        (
            "Q14",
            "임상 의사결정 지원이 아닌 교육·설명 용도로 한정할 때, 시스템 프롬프트에 넣을 역할 문장 초안을 2~3문장으로 쓰라.",
        ),
        (
            "Q15",
            "사상의학 용어를 비전문가에게 전달할 때 쓸 비유·주의사항(오해 소지)을 한 단락으로 정리하라.",
        ),
        (
            "Q16",
            "다국어(한·영) 번역 시 의미가 흔들리기 쉬운 용어 5개를 골라, 번역 시 주의점만 bullet로 쓰라.",
        ),
        (
            "Q17",
            "로그·감사 관점에서, 어떤 질의·응답 메타데이터(체질 후보, 신뢰도, 인용 출처)를 남겨야 재현성 논의에 도움이 되는지 나열하라.",
        ),
        (
            "Q18",
            "동일 질문을 노트북 소스 구성이 다른 두 버전에 던질 때, 응답 차이를 정리하는 비교표 헤더(열 이름)만 제안하라.",
        ),
    ],
    "c": [
        (
            "Q19",
            "사상체질과 서양 의학 분류(예: 증후군·대사)를 직접 동일시하지 말아야 할 이유를 원전의 경계 개념과 연결해 설명하라.",
        ),
        (
            "Q20",
            "생물학적 메커니즘이 불충분하다고 본 주장이 있다면, 원전·보고서에 근거한 연구 과제(가설·실험 설계 아이디어)를 2~3줄로 제시하라.",
        ),
        (
            "Q21",
            "심리척도(Big5 등)와 사상 네 유형을 비유적으로 연결할 때의 한계를 명시하라.",
        ),
        (
            "Q22",
            "환자 안전: 자가 진단·자가 처방을 유도할 수 있는 표현을 피하기 위한 대체 문구 예시를 3개 제시하라.",
        ),
        (
            "Q23",
            "한의·의료법 맥락에서 AI 출력이 가질 수 있는 법적·윤리 리스크를 일반론으로만(구체 조문 인용 없이) bullet로 정리하라.",
        ),
        (
            "Q24",
            "이 노트북 소스만으로 검증 가능한 사실과, 외부 임상 데이터가 필요한 주장을 구분하는 질문 1개를 직접 작성하라.",
        ),
    ],
}


def run_batch(batch: str, append: bool = False) -> int:
    items = QUESTIONS[batch]
    suffix = "" if batch == "a" else f"_{batch}"
    out_path = OUT_DIR / f"ijeoma_query_set_run_v1{suffix}.jsonl"
    sum_path = OUT_DIR / f"ijeoma_query_set_run_v1{suffix}_summary.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not append and out_path.exists():
        out_path.unlink()

    rows: list[dict] = []
    for query_id, question in items:
        t0 = time.time()
        proc = subprocess.run(
            ["nlm", "notebook", "query", UUID, question],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
        )
        elapsed = round(time.time() - t0, 1)
        ok = proc.returncode == 0
        answer = None
        conv = None
        if ok:
            try:
                payload = json.loads(proc.stdout)
                val = payload.get("value") or payload
                answer = val.get("answer")
                conv = val.get("conversation_id")
            except json.JSONDecodeError:
                ok = False
        row = {
            "schema": "ijeoma_query_set_run_v1",
            "batch": batch,
            "query_id": query_id,
            "question": question,
            "ok": ok,
            "elapsed_s": elapsed,
            "conversation_id": conv,
            "answer_preview": (answer or proc.stderr or proc.stdout or "")[:800],
            "answer_chars": len(answer or ""),
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        rows.append(row)
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(
            json.dumps(
                {"query_id": query_id, "ok": ok, "elapsed_s": elapsed, "chars": row["answer_chars"]},
                ensure_ascii=False,
            ),
            flush=True,
        )
        time.sleep(1.0)

    summary = {
        "schema": "ijeoma_query_set_run_v1_summary",
        "batch": batch,
        "notebook_uuid": UUID,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(rows),
        "ok": sum(1 for r in rows if r["ok"]),
        "fail": sum(1 for r in rows if not r["ok"]),
        "avg_elapsed_s": round(sum(r["elapsed_s"] for r in rows) / len(rows), 1) if rows else 0,
        "jsonl": str(out_path.relative_to(ROOT)).replace("\\", "/"),
    }
    sum_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False))
    return 0 if summary["fail"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch",
        choices=["a", "b", "c", "bc"],
        default="b",
        help="Query set section: a=Q01-10, b=Q11-18, c=Q19-24, bc=b then c",
    )
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()
    if args.batch == "bc":
        rc = run_batch("b", append=args.append)
        rc |= run_batch("c", append=args.append)
        return rc
    return run_batch(args.batch, append=args.append)


if __name__ == "__main__":
    sys.exit(main())
