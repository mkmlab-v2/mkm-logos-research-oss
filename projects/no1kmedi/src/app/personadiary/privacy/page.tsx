import type { Metadata } from "next";
import { PersonadiaryLegalPage } from "@/components/PersonadiaryLegalPage";
import { personadiaryCopy } from "@/content/personadiaryCopy";

export const metadata: Metadata = {
  title: `개인정보 처리방침 | ${personadiaryCopy.brand.name}`,
  description:
    "personadiary.com 프리뷰 단계 개인정보 처리 안내. 일기 저장·결제 미제공.",
};

export default function PersonadiaryPrivacyPage() {
  return (
    <PersonadiaryLegalPage title="개인정보 처리방침 (프리뷰)">
      <span className="pd-legal-tag">preview_only · 법무 검토 전 초안</span>
      <p>
        본 방침은 <strong>personadiary.com</strong> 콘셉트 프리뷰에 적용됩니다.
        임상·투자·법률 조언을 제공하지 않으며, mkmlife·jema-ai CDSS와 동일
        서비스가 아닙니다.
      </p>
      <h2>1. 수집 항목 (현재)</h2>
      <ul>
        <li>
          <strong>프리뷰 홈·데모:</strong> 사용자 일기 본문·계정 정보를 서버에
          저장하지 않습니다.
        </li>
        <li>
          <strong>문의 메일:</strong> hello@personadiary.com 등으로 보내신
          이메일 주소·문의 내용(자발적 제공).
        </li>
        <li>
          <strong>접속 로그:</strong> 호스팅·CDN(Cloudflare)·VPS 운영에 따른
          일반 접속 메타(법적 보관 기간 내).
        </li>
      </ul>
      <h2>2. 이용 목적</h2>
      <ul>
        <li>프리뷰 안내·사전 알림 회신</li>
        <li>서비스 안정성·보안·남용 방지</li>
        <li>법령상 의무 이행</li>
      </ul>
      <h2>3. 보관·파기</h2>
      <p>
        문의 메일은 회신·운영 목적 달성 후 내부 정책·법령에 따라 파기합니다.
        프리뷰 단계에서 일기 데이터 영구 저장소는 운영하지 않습니다.
      </p>
      <h2>4. 제3자 제공·국외 이전</h2>
      <p>
        호스팅·이메일 라우팅(Cloudflare 등) 수준의 처리 위탁이 있을 수 있습니다.
        별도 동의 없이 마케팅 제3자에게 판매하지 않습니다.
      </p>
      <h2>5. 문의</h2>
      <p>
        개인정보 관련 문의:{" "}
        <a href="mailto:hello@personadiary.com">hello@personadiary.com</a>
      </p>
      <p>
        <em>
          본문은 프리뷰용 초안이며, 본선(저장·결제) 전 법무 검토·갱신이
          필요합니다.
        </em>
      </p>
    </PersonadiaryLegalPage>
  );
}
