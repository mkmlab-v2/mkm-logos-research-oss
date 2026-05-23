import type { Metadata } from "next";
import { PersonadiaryLegalPage } from "@/components/PersonadiaryLegalPage";
import { personadiaryCopy } from "@/content/personadiaryCopy";

export const metadata: Metadata = {
  title: `이용약관 | ${personadiaryCopy.brand.name}`,
  description:
    "personadiary.com 프리뷰 이용약관 초안. 의료·투자 조언·실매매 합선 없음.",
};

export default function PersonadiaryTermsPage() {
  return (
    <PersonadiaryLegalPage title="이용약관 (프리뷰)">
      <span className="pd-legal-tag">preview_only · 법무 검토 전 초안</span>
      <p>
        personadiary.com(이하 &quot;프리뷰&quot;)는 AI 마음 일기·리플렉션
        콘셉트를 검증하는 <strong>비상용·무료 프리뷰</strong>입니다.
      </p>
      <h2>1. 서비스 범위</h2>
      <ul>
        <li>프리뷰는 일기 저장·동기화·유료 결제를 제공하지 않습니다.</li>
        <li>
          /demo 는 [HYPO] 콘셉트 데모이며, 연구·시연 목적입니다.
        </li>
        <li>
          심화 관측·쇼룸은 jemaai.cloud 등 <strong>별도 도메인</strong>에서
          제공되며 본 약관과 자동으로 동일하지 않습니다.
        </li>
      </ul>
      <h2>2. 금지·면책</h2>
      <ul>
        <li>의료 진단·치료·투자·법률 자문을 대체하지 않습니다.</li>
        <li>성과·수익·적중률·무손실·100% 복원 등을 보장하지 않습니다.</li>
        <li>Track A 실매매·자동 매매와 연동되지 않습니다.</li>
      </ul>
      <h2>3. 이용자 의무</h2>
      <p>
        불법·타인 권리 침해·과장된 의료·투자 주장 등을 게시·전송하지 않습니다.
        프리뷰는 예고 없이 변경·중단될 수 있습니다.
      </p>
      <h2>4. 지식재산</h2>
      <p>
        UI·카피·데모 콘텐츠의 권리는 운영자 또는 라이선스에 따릅니다. 무단
        복제·상업적 2차 배포를 금합니다.
      </p>
      <h2>5. 문의</h2>
      <p>
        <a href="mailto:hello@personadiary.com">hello@personadiary.com</a>
      </p>
      <p>
        <em>본선 서비스 오픈 전 법무 검토·약관 갱신이 필요합니다.</em>
      </p>
    </PersonadiaryLegalPage>
  );
}
