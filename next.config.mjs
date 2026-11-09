const basePath = process.env.NEXT_PUBLIC_BASE_PATH !== undefined
  ? process.env.NEXT_PUBLIC_BASE_PATH
  : "/us/aca-calc";

// policyengine.org serves this app at /us/aca-calc through policyengine-app-v2's
// zone rewrite (website/src/data/appZoneRoutes.ts) to aca-calc.vercel.app. A
// visit straight to that host goes to the same page on policyengine.org.
const PUBLIC_URL = "https://www.policyengine.org/us/aca-calc";
// Vercel sets x-forwarded-host to the host the visitor asked for and overwrites
// any value the visitor sends: aca-calc.vercel.app on a direct visit,
// www.policyengine.org on a request policyengine.org proxies. Previews have
// hosts of their own, so these rules leave them alone too.
const directVisit = [
  { type: "header", key: "x-forwarded-host", value: "aca-calc\\.vercel\\.app" },
];

const nextConfig = {
  ...(basePath ? { basePath } : {}),
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
  distDir: "dist",
  async redirects() {
    return [
      // The host's root, outside the basePath.
      { source: "/", basePath: false, has: directVisit, destination: PUBLIC_URL, permanent: true },
      // The bare basePath. Without this rule Vercel sends it to PUBLIC_URL + "/", a second hop.
      { source: "/", has: directVisit, destination: PUBLIC_URL, permanent: true },
      { source: "/:path*", has: directVisit, destination: `${PUBLIC_URL}/:path*`, permanent: true },
    ];
  },
};

export default nextConfig;
