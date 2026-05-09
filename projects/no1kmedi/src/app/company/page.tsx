export const metadata = {
  title: "Company | JEMA AI",
  description: "Company information for Moksori Network Co., Ltd.",
};

export default function CompanyPage() {
  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1.25rem 3rem" }}>
      <h1>Company</h1>
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
        <a href="/">Back to Home</a>
      </p>
    </main>
  );
}
