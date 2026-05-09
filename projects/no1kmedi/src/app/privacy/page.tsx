export const metadata = {
  title: "Privacy Policy | JEMA AI",
  description: "Privacy policy for MKM services.",
};

export default function PrivacyPage() {
  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1.25rem 3rem", lineHeight: 1.7 }}>
      <h1>Privacy Policy</h1>
      <p>
        We process personal data only for service operation, user support, and lawful obligations. Data handling
        follows applicable regulations and internal security policy.
      </p>
      <ul>
        <li>Collection: minimum required fields for support and service operation.</li>
        <li>Retention: only for required period by policy and law.</li>
        <li>Deletion: securely removed when retention period expires.</li>
        <li>Contact: support@mkmlife.com</li>
      </ul>
      <p>
        <a href="/">Back to Home</a>
      </p>
    </main>
  );
}
