import { PolicyEngineShell } from "@policyengine/ui-kit/layout";
import "@policyengine/ui-kit/styles.css";

import "./globals.css";
import Script from "next/script";

export const metadata = {
  title: "ACA Calculator",
  description: "PolicyEngine ACA premium tax credit calculator and subsidy cliff explorer",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <PolicyEngineShell country="us">{children}        </PolicyEngineShell>
        {/* Google Analytics: policyengine.org's GA4 property; this app is served at policyengine.org/us/aca-calc through a rewrite, where the main site's GA does not reach. */}
        {process.env.NODE_ENV === "production" && (
          <>
            <Script
              src="https://www.googletagmanager.com/gtag/js?id=G-2YHG89FY0N"
              strategy="afterInteractive"
            />
            <Script id="google-analytics" strategy="afterInteractive">
              {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-2YHG89FY0N');`}
            </Script>
          </>
        )}
      </body>
    </html>
  );
}
