import type { NextConfig } from "next";

// The browser talks to the API through this same origin (/api, /media), so the httpOnly
// session cookie stays first-party and no CORS preflights are needed.
// The rewrites are compiled at build time, so API_INTERNAL_URL must be set when building, not only at runtime.
const apiUrl = (process.env.API_INTERNAL_URL ?? "http://localhost:8000").replace(/\/+$/, "");
if (!process.env.API_INTERNAL_URL && process.env.NODE_ENV === "production") {
  // On Render (which sets RENDER=true) a localhost fallback can never work, so stop the deploy here.
  if (process.env.RENDER) {
    throw new Error("API_INTERNAL_URL is not set. Add it to this Render service's environment, e.g. https://<api>.onrender.com");
  }
  console.warn(`API_INTERNAL_URL is not set: /api and /media will be proxied to ${apiUrl}.`);
}

const nextConfig: NextConfig = {
  reactCompiler: true,
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
      { source: "/media/:path*", destination: `${apiUrl}/media/:path*` },
    ];
  },
  // Old dashboard paths, kept so bookmarks and earlier links still work.
  async redirects() {
    return [
      { source: "/dashboard/renter/requests", destination: "/dashboard/renter/house-search", permanent: true },
      { source: "/dashboard/agent/bookings", destination: "/dashboard/agent/inspection-slots", permanent: true },
      { source: "/dashboard/reviewer/audit", destination: "/dashboard/reviewer/audit-log", permanent: true },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};

export default nextConfig;
