import { Fragment } from "react";
import { siteCopy } from "@/content/siteCopy";
import { SiteHeader } from "@/components/SiteHeader";
import { FreeValidationLeadForm } from "@/components/FreeValidationLeadForm";
import { ContactActionLinks } from "@/components/ContactActionLinks";
import { AdvancedConsultForm } from "@/components/AdvancedConsultForm";
import { PatientPreSurveyForm } from "@/components/PatientPreSurveyForm";
import { BasicHealthChatCard } from "@/components/BasicHealthChatCard";

export default function HomePage() {
  const c = siteCopy;

  return (
    <>
      <a className="skip" href="#main">
        본문으로 건너뛰기
      </a>
      <SiteHeader nav={c.nav} brand={c.header} />
      <main id="main">
        <section className="hero" id="top" aria-labelledby="hero-title">
          <div className="hero-orb hero-orb-a" aria-hidden="true" />
          <div className="hero-orb hero-orb-b" aria-hidden="true" />
          <span className="eyebrow">{c.hero.eyebrow}</span>
          <h1 id="hero-title">{c.hero.title}</h1>
          <p className="hero-lead">{c.hero.subtitle}</p>
          <div className="hero-cta">
            <a className="btn btn-primary" href="#patient-intake">
              {c.hero.cta_primary}
            </a>
            <a className="btn btn-ghost" href="#advanced-consult">
              {c.hero.cta_secondary}
            </a>
          </div>
          <div className="hero-role-cta">
            <article className="card">
              <h3>환자/보호자</h3>
              <p>기본 건강·체질·통증 정보를 먼저 입력하면 의료진 검토를 빠르게 시작할 수 있습니다.</p>
              <a className="btn btn-primary" href="#patient-intake">
                사전문진 입력
              </a>
            </article>
            <article className="card">
              <h3>한의사/의료진</h3>
              <p>사상의학 중심 CDSS 화면에서 근거 기반 초안을 확인하고 최종 판단을 확정합니다.</p>
              <a className="btn btn-ghost" href="#advanced-consult">
                의료진 화면 이동
              </a>
            </article>
          </div>
          <div className="hero-proof" role="list" aria-label="핵심 가치">
            <span role="listitem">근거 출처 매핑</span>
            <span role="listitem">의료진 최종판단 고정</span>
            <span role="listitem">일반인 무료 사전 리포트</span>
          </div>
        </section>

        <section id="trust" aria-label="신뢰 지표">
          <div className="trust-strip" role="list">
            {c.trust.items.map((item) => (
              <article key={item.label} className="trust-item" role="listitem">
                <p>{item.label}</p>
                <strong>{item.value}</strong>
              </article>
            ))}
          </div>
        </section>

        <section id="public-solution" aria-labelledby="public-solution-title">
          <h2 id="public-solution-title">{c.public_solution.title}</h2>
          <p className="section-lead">{c.public_solution.section_lead}</p>
          <div className="grid-3">
            {c.public_solution.cards.map((item) => (
              <article key={item.title} className="card">
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
          <div className="section-cta">
            <a className="btn btn-primary" href="#patient-intake">
              {c.public_solution.cta_primary}
            </a>
            <a className="btn btn-ghost" href="#contact">
              {c.public_solution.cta_secondary}
            </a>
          </div>
        </section>

        <section id="about" aria-labelledby="about-title">
          <h2 id="about-title">{c.about.title}</h2>
          <p className="section-lead">{c.about.section_lead}</p>
          <div className="grid-3">
            {c.value_props.map((vp) => (
              <article key={vp.title} className="card">
                <h3>{vp.title}</h3>
                <p>{vp.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="safety" aria-labelledby="safety-title">
          <h2 id="safety-title">{c.safety.title}</h2>
          <div className="notice-box">
            <ul>
              {c.safety.items.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        </section>

        <section id="workflow" aria-labelledby="flow-title">
          <h2 id="flow-title">{c.workflow.title}</h2>
          <p className="section-lead">{c.workflow.section_lead}</p>
          <div className="steps" role="list">
            {c.workflow.steps.map((step, i) => (
              <Fragment key={step}>
                {i > 0 ? (
                  <span className="arrow" aria-hidden="true">
                    →
                  </span>
                ) : null}
                <span role="listitem">{step}</span>
              </Fragment>
            ))}
          </div>
        </section>

        <section id="premium-story" aria-labelledby="premium-story-title">
          <h2 id="premium-story-title">AI 한의학 랜딩 경험을 더 명확하게</h2>
          <p className="section-lead">
            일반인에게는 이해하기 쉬운 사전 리포트 경험을, 의료진에게는 근거 중심 임상 정리 경험을
            한 화면 흐름 안에서 연결합니다.
          </p>
          <div className="premium-grid">
            <article className="premium-panel">
              <p className="premium-label">Public</p>
              <h3>쉽게 이해되는 AI 한의학 안내</h3>
              <p>입력 부담을 줄인 문진과 결과 요약으로 일반인도 서비스 가치를 빠르게 체감합니다.</p>
            </article>
            <article className="premium-panel">
              <p className="premium-label">Clinical</p>
              <h3>차트·진료 준비 보조로 바로 연결</h3>
              <p>문진/상담 맥락을 정리해 의료진이 기록 반영과 환자 설명에 집중할 수 있도록 돕습니다.</p>
            </article>
          </div>
        </section>

        <BasicHealthChatCard />

        <PatientPreSurveyForm />

        <AdvancedConsultForm />

        <section id="contact" aria-labelledby="contact-title">
          <h2 id="contact-title">{c.contact.title}</h2>
          <p className="section-lead">{c.contact.section_lead}</p>
          <ContactActionLinks email={c.footer.email} label={c.contact.email_label} />
          <FreeValidationLeadForm />
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand">{c.footer.company_line}</div>
          <div className="footer-meta">
            <p>주소: {c.footer.address}</p>
            <p>사업자등록번호: {c.footer.biz_reg}</p>
          </div>
          <div className="footer-legal">{c.footer.rights}</div>
        </div>
      </footer>
    </>
  );
}
