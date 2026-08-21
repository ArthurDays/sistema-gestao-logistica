import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "LogiSync — Gestão Logística",
    short_name: "LogiSync",
    description: "Gestão inteligente de rotas e desempenho de veículos",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f7fb",
    theme_color: "#031329",
    orientation: "portrait-primary",
    icons: [
      { src: "/logisync-logo.png", sizes: "1024x1024", type: "image/png" },
    ],
  };
}
