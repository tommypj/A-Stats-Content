import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "A-Stats — AI-Powered SEO & Content Platform";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #2e352e 0%, #404d40 40%, #627862 100%)",
          fontFamily: "sans-serif",
        }}
      >
        {/* Logo area */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "32px",
          }}
        >
          <div
            style={{
              width: "72px",
              height: "72px",
              borderRadius: "18px",
              background: "rgba(255,255,255,0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "36px",
            }}
          >
            ✦
          </div>
          <div
            style={{
              fontSize: "56px",
              fontWeight: 700,
              color: "#fdfcfa",
              letterSpacing: "-1px",
            }}
          >
            A-Stats
          </div>
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: "28px",
            color: "#e9dcc8",
            textAlign: "center",
            maxWidth: "800px",
            lineHeight: 1.4,
          }}
        >
          AI-Powered SEO & Content Platform
        </div>

        {/* Features row */}
        <div
          style={{
            display: "flex",
            gap: "32px",
            marginTop: "40px",
          }}
        >
          {["SEO Articles", "AEO Tracking", "Bulk Generation", "Analytics"].map(
            (feature) => (
              <div
                key={feature}
                style={{
                  padding: "10px 24px",
                  borderRadius: "100px",
                  background: "rgba(255,255,255,0.12)",
                  color: "#f3ece0",
                  fontSize: "18px",
                  fontWeight: 500,
                }}
              >
                {feature}
              </div>
            )
          )}
        </div>

        {/* URL */}
        <div
          style={{
            position: "absolute",
            bottom: "32px",
            fontSize: "18px",
            color: "rgba(253,252,250,0.5)",
          }}
        >
          a-stats.app
        </div>
      </div>
    ),
    { ...size }
  );
}
