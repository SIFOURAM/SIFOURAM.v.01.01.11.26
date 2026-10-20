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

export const DEFAULTS = { bold: false, font: "" };

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
}

export function getAppearance() {
  try {
    const { scale, color, view, ...appearance } = JSON.parse(localStorage.getItem("si4am_appearance") || "{}");
    return { ...DEFAULTS, ...appearance };
  }
  catch { return { ...DEFAULTS }; }
}

export function setAppearance(a) {
  localStorage.setItem("si4am_appearance", JSON.stringify(a));
  applyAppearance(a);
}
