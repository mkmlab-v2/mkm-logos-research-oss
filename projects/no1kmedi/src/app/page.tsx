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
              <p>질문형 AI 상담으로 건강정보를 먼저 정리하고, 제휴 한의원 연결까지 한 번에 이어집니다.</p>
              <a className="btn btn-primary" href="/consumer">
                일반인 상담 입장
              </a>
            </article>
            <article className="card card-lift">
              <h3>한의사/의료진</h3>
              <p>입력된 환자 정보를 바탕으로 citation 기반 차트 초안을 만들고 최종 판단은 의료진이 확정합니다.</p>
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
              <p className="premium-label">Brand Motion</p>
              <h2 id="brand-motion-title">대외 홍보용 시네마틱 섹션</h2>
              <p className="section-lead">
                일반인 대상 랜딩의 첫 인상을 강화하기 위해 모션 영상과 반응형 글래스 레이어를 결합했습니다.
                의료진 보조라는 핵심 메시지는 유지하면서도 브랜드 완성도를 높입니다.
              </p>
              <div className="hero-proof" role="list" aria-label="브랜드 모션 특징">
                <span role="listitem">Autoplay mute motion</span>
                <span role="listitem">Glass depth overlay</span>
                <span role="listitem">Enterprise-style visual rhythm</span>
              </div>
            </article>
            <div className="brand-motion-stage card-lift" aria-hidden="true">
              <div className="brand-motion-canvas" />
              <div className="brand-motion-beam brand-motion-beam-a" />
              <div className="brand-motion-beam brand-motion-beam-b" />
              <div className="brand-motion-grain" />
              <div className="brand-motion-tint" />
              <div className="brand-motion-label">JEMA AI MOTION SCENE</div>
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

        <section id="premium-story" aria-labelledby="premium-story-title">
          <h2 id="premium-story-title">AI 한의학 랜딩 경험을 더 명확하게</h2>
          <p className="section-lead">
            일반인에게는 이해하기 쉬운 사전 리포트 경험을, 의료진에게는 근거 중심 임상 정리 경험을
            한 화면 흐름 안에서 연결합니다.
          </p>
          <div className="premium-grid">
            <article className="premium-panel card-lift">
              <p className="premium-label">Public</p>
              <h3>쉽게 이해되는 AI 한의학 안내</h3>
              <p>챗 인터페이스와 사전문진이 연결되어 일반인이 즉시 체감 가능한 상담 흐름으로 진입합니다.</p>
            </article>
            <article className="premium-panel card-lift">
              <p className="premium-label">Clinical</p>
              <h3>차트·진료 준비 보조로 바로 연결</h3>
              <p>환자 입력 데이터와 임상 정보를 분리 레인으로 요약해 의료진 기록 정확도를 높입니다.</p>
            </article>
          </div>
          <div className="section-cta">
            <a className="btn btn-primary" href="/consumer">
              일반인 체험 시작
            </a>
            <a className="btn btn-ghost" href="/clinician">
              의료진 체험 시작
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
