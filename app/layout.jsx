import "./globals.css";
import PolicyEngineHeader from "../components/PolicyEngineHeader";

export const metadata = {
  title: "ACA Calculator",
  description: "PolicyEngine ACA premium tax credit calculator and subsidy cliff explorer",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <PolicyEngineHeader />
        {children}
      </body>
    </html>
  );
}
