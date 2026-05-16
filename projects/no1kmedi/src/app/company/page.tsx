export const metadata = {
  title: "회사 소개 | JEMA AI",
  description: "주식회사 목소리네트워크 법적 고지 및 연락처.",
};

export default function CompanyPage() {
  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1.25rem 3rem" }}>
      <h1>회사 소개</h1>
      <p>Moksori Network Co., Ltd. (Sub-brand: MKMLAB)</p>
      <ul>
        <li>CEO: Ki-ryun Lee</li>
        <li>Business Registration No.: 628-86-01742</li>
        <li>
          Business Address: 2301-ho, 102-dong, 24 Digital-ro, Gwangmyeong-si, Gyeonggi-do, 14241, Republic of Korea
        </li>
        <li>Support Email: support@mkmlife.com</li>
      </ul>
      <p>
        <a href="/">홈으로</a>
      </p>
    </main>
  );
}
