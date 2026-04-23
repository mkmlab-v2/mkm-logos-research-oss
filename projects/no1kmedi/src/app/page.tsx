import { Fragment } from "react";
import { siteCopy } from "@/content/siteCopy";
import { SiteHeader } from "@/components/SiteHeader";
import { FreeValidationLeadForm } from "@/components/FreeValidationLeadForm";
import { ContactActionLinks } from "@/components/ContactActionLinks";

export const dynamic = "force-dynamic";

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
          <div className="hero-grid-overlay" aria-hidden="true" />
          <span className="eyebrow">{c.hero.eyebrow}</span>
          <h1 id="hero-title">{c.hero.title}</h1>
          <p className="hero-lead">{c.hero.subtitle}</p>
          <div className="hero-cta">
            <a className="btn btn-primary" href="/consumer">
              일반인 시작하기
            </a>
            <a className="btn btn-ghost" href="/clinician">
              한의사 시작하기
            </a>
          </div>
          <div className="hero-role-cta">
            <article className="card card-lift">
              <h3>환자/보호자</h3>
              <p>간단한 문진 입력으로 상담 전 핵심 정보를 정리하고, 필요 시 제휴 한의원 상담으로 연결합니다.</p>
              <a className="btn btn-primary" href="/consumer">
                일반인 상담 입장
              </a>
            </article>
            <article className="card card-lift">
              <h3>한의사/의료진</h3>
              <p>문진·상담 데이터를 기반으로 진료 준비 초안을 정리하며, 최종 진단·처방 판단은 의료진이 확정합니다.</p>
              <a className="btn btn-ghost" href="/clinician">
                의료진 보조 입장
              </a>
            </article>
          </div>
          <div className="hero-proof" role="list" aria-label="핵심 가치">
            <span role="listitem">근거 출처 매핑</span>
            <span role="listitem">의료진 최종판단 고정</span>
            <span role="listitem">일반인 무료 사전 리포트</span>
          </div>
        </section>

        <section id="brand-motion" aria-labelledby="brand-motion-title">
          <div className="brand-motion-grid">
            <article className="brand-motion-copy">
              <p className="premium-label">{c.concept_block.label}</p>
              <h2 id="brand-motion-title">{c.concept_block.title}</h2>
              <p className="section-lead">
                {c.concept_block.lead}
              </p>
              <div className="hero-proof" role="list" aria-label="브랜드 모션 특징">
                {c.concept_block.proof_items.map((item) => (
                  <span key={item} role="listitem">{item}</span>
                ))}
              </div>
            </article>
            <div className="brand-motion-stage card-lift" aria-hidden="true">
              <div className="brand-motion-canvas" />
              <div className="brand-motion-beam brand-motion-beam-a" />
              <div className="brand-motion-beam brand-motion-beam-b" />
              <div className="brand-motion-grain" />
              <div className="brand-motion-tint" />
              <div className="brand-motion-label">{c.concept_block.stage_label}</div>
            </div>
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
            <a className="btn btn-primary" href="/consumer">
              일반인 AI 상담으로 이동
            </a>
            <a className="btn btn-ghost" href="/clinician">
              의료진 보조 화면 보기
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

        <section id="clinic-o2o" aria-labelledby="clinic-o2o-title">
          <h2 id="clinic-o2o-title">한의원 QR 접수 운영 가이드</h2>
          <p className="section-lead">
            원내 대기실 QR로 환자가 스마트폰에서 사전 문진을 완료하고, 접수 시 문진 코드(PIN)만 제시하면
            의료진 화면에서 즉시 불러올 수 있도록 설계합니다.
          </p>
          <div className="grid-3">
            <article className="card">
              <h3>대기실 안내판 문구</h3>
              <p>
                &quot;진료 전 2분 문진&quot; QR을 스캔해 주세요. 입력 완료 후 발급되는 문진 코드를 접수대에 보여주세요.
              </p>
            </article>
            <article className="card">
              <h3>접수대 1페이지 스크립트</h3>
              <p>
                &quot;문진 코드가 있으신가요? 코드와 성함을 확인해 드릴게요.&quot; 확인 후 의료진 화면에서 PIN으로 환자
                문진을 호출합니다.
              </p>
            </article>
            <article className="card">
              <h3>의료법 고지 고정</h3>
              <p>
                환자 화면은 웰니스 기반 사전 문진/정보 제공이며, 최종 진단·처방·차트 확정은 한의사가 수행합니다.
              </p>
            </article>
          </div>
          <div className="section-cta">
            <a className="btn btn-primary" href="/consumer">
              QR용 환자 문진 화면 열기
            </a>
            <a className="btn btn-ghost" href="/reception">
              접수대 PIN 조회 화면
            </a>
            <a className="btn btn-ghost" href="/clinician">
              의료진 보조 화면 열기
            </a>
          </div>
        </section>

        <section id="premium-story" aria-labelledby="premium-story-title">
          <h2 id="premium-story-title">{c.landing_flow.title}</h2>
          <p className="section-lead">{c.landing_flow.lead}</p>
          <div className="premium-grid">
            {c.landing_flow.cards.map((item) => (
              <article key={item.title} className="premium-panel card-lift">
                <p className="premium-label">{item.label}</p>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
          <div className="section-cta">
            <a className="btn btn-primary" href="/consumer">
              {c.landing_flow.cta_primary}
            </a>
            <a className="btn btn-ghost" href="/clinician">
              {c.landing_flow.cta_secondary}
            </a>
          </div>
        </section>

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
