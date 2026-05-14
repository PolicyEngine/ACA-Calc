import "./globals.css";

export const metadata = {
  title: "ACA Calculator",
  description: "PolicyEngine ACA premium tax credit calculator and subsidy cliff explorer",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
