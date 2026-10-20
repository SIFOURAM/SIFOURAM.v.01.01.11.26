export const FONTS = [
  { key: "jakarta", label: "Plus Jakarta Sans", css: "'Plus Jakarta Sans', sans-serif", google: "Plus+Jakarta+Sans:wght@400;500;600;700;800" },
  { key: "inter", label: "Inter", css: "'Inter', sans-serif", google: "Inter:wght@400;500;600;700" },
  { key: "poppins", label: "Poppins", css: "'Poppins', sans-serif", google: "Poppins:wght@400;500;600;700" },
  { key: "nunito", label: "Nunito", css: "'Nunito', sans-serif", google: "Nunito:wght@400;600;700;800" },
  { key: "outfit", label: "Outfit", css: "'Outfit', sans-serif", google: "Outfit:wght@400;500;600;700;800" },
  { key: "roboto", label: "Roboto", css: "'Roboto', sans-serif", google: "Roboto:wght@400;500;700" },
  { key: "lato", label: "Lato", css: "'Lato', sans-serif", google: "Lato:wght@400;700;900" },
  { key: "montserrat", label: "Montserrat", css: "'Montserrat', sans-serif", google: "Montserrat:wght@400;500;600;700" },
  { key: "merriweather", label: "Merriweather (Serif)", css: "'Merriweather', serif", google: "Merriweather:wght@400;700" },
  { key: "jetbrains", label: "JetBrains Mono", css: "'JetBrains Mono', monospace", google: "JetBrains+Mono:wght@400;600" },
  { key: "oswald", label: "Oswald (Athletic)", css: "'Oswald', sans-serif", google: "Oswald:wght@400;500;600;700" },
  { key: "javanese", label: "Noto Sans Javanese", css: "'Noto Sans Javanese', sans-serif", google: "Noto+Sans+Javanese:wght@400;700" },
];

export const DEFAULTS = { bold: false, font: "", view: "web" };

const loaded = new Set();
function loadFont(key) {
  const f = FONTS.find((x) => x.key === key);
  if (!f || loaded.has(key)) return;
  loaded.add(key);
  const l = document.createElement("link");
  l.rel = "stylesheet";
  l.href = `https://fonts.googleapis.com/css2?family=${f.google}&display=swap`;
  document.head.appendChild(l);
}

function hexToHsl(hex) {
  let h = (hex || "").replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  if (h.length !== 6) return null;
  const r = parseInt(h.slice(0, 2), 16) / 255, g = parseInt(h.slice(2, 4), 16) / 255, b = parseInt(h.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let hue = 0, s = 0; const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: hue = (g - b) / d + (g < b ? 6 : 0); break;
      case g: hue = (b - r) / d + 2; break;
      default: hue = (r - g) / d + 4;
    }
    hue /= 6;
  }
  return `${Math.round(hue * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}

export function applyAppearance(a) {
  const root = document.documentElement;
  if (a.font) {
    const f = FONTS.find((x) => x.key === a.font) || FONTS[0];
    loadFont(f.key);
    root.style.setProperty("--app-font", f.css);
    document.body.classList.add("app-font");
  } else {
    document.body.classList.remove("app-font");
  }
  document.body.classList.toggle("app-bold", !!a.bold);
  document.body.classList.remove("vm-web", "vm-tablet", "vm-mobile");
  document.body.classList.add(`vm-${a.view || "web"}`);
  window.dispatchEvent(new Event("appearancechange"));
}

export function getAppearance() {
  try {
    const { scale, color, ...appearance } = JSON.parse(localStorage.getItem("si4am_appearance") || "{}");
    return { ...DEFAULTS, ...appearance };
  }
  catch { return { ...DEFAULTS }; }
}

export function setAppearance(a) {
  localStorage.setItem("si4am_appearance", JSON.stringify(a));
  applyAppearance(a);
}
