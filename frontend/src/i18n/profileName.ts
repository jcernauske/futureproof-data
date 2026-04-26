import type { AppLocale } from "./locales";

const ES: Record<string, string> = {
  // ADJECTIVES_1
  brave: "Valiente", bold: "Audaz", bright: "Brillante", calm: "Sereno",
  clever: "Astuto", cosmic: "Cósmico", cozy: "Acogedor", daring: "Atrevido",
  dancing: "Danzante", dreamy: "Soñador", eager: "Ansioso",
  electric: "Eléctrico", epic: "Épico", fearless: "Intrépido",
  fierce: "Feroz", free: "Libre", gentle: "Gentil", glad: "Alegre",
  glowing: "Radiante", golden: "Dorado", grand: "Grandioso",
  happy: "Feliz", humble: "Humilde", keen: "Agudo", kind: "Amable",
  lively: "Vivaz", lucky: "Afortunado", loyal: "Leal", magic: "Mágico",
  merry: "Jovial", mighty: "Poderoso", noble: "Noble", plucky: "Valeroso",
  proud: "Orgulloso", quick: "Rápido", quiet: "Tranquilo", rad: "Genial",
  ready: "Listo", rising: "Ascendente", roaming: "Errante",
  shining: "Reluciente", smooth: "Suave", snappy: "Ágil",
  soaring: "Elevado", sparky: "Chispeante", speedy: "Veloz",
  spirited: "Animoso", steady: "Firme", stellar: "Estelar",
  stoked: "Entusiasta",

  // ADJECTIVES_2
  agile: "Ágil", awesome: "Increíble", breezy: "Fresco", chill: "Relajado",
  clear: "Claro", crisp: "Nítido", curious: "Curioso", dapper: "Elegante",
  deft: "Diestro", earnest: "Sincero", fair: "Justo", fancy: "Refinado",
  fleet: "Ligero", fluffy: "Esponjoso", focused: "Enfocado",
  fresh: "Fresco", frisky: "Juguetón", fun: "Divertido",
  fuzzy: "Peludo", groovy: "Genial", gutsy: "Valiente", handy: "Hábil",
  hearty: "Cordial", honest: "Honesto", jazzy: "Llamativo",
  joyful: "Gozoso", jumpy: "Saltarín", legit: "Auténtico",
  nimble: "Ágil", nifty: "Ingenioso", peppy: "Animado", perky: "Alegre",
  plush: "Mullido", polished: "Pulido", prime: "Primo",
  pumped: "Motivado", quirky: "Peculiar", rare: "Singular",
  real: "Real", robust: "Robusto", savvy: "Sagaz", sharp: "Agudo",
  slick: "Hábil", snug: "Cómodo", solid: "Sólido", spry: "Vivaz",
  sure: "Seguro", swift: "Veloz", true: "Verdadero", vivid: "Vívido",

  // ANIMALS
  bear: "Oso", bunny: "Conejito", turtle: "Tortuga",
  chipmunk: "Ardilla", fox: "Zorro", owl: "Búho",
  penguin: "Pingüino", cat: "Gato",
};

export function localizeProfileName(
  name: string,
  locale: AppLocale,
): string {
  if (locale !== "es") return name;
  return name
    .split(" ")
    .map((word) => {
      const stripped = word.replace(/\d+$/, "");
      const digits = word.slice(stripped.length);
      const translated = ES[stripped.toLowerCase()];
      return translated ? translated + digits : word;
    })
    .join(" ");
}
