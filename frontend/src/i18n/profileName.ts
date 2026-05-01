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

// Arabic dictionary. Same word universe as ES — every key in ES is
// represented here so Arabic users see a fully Arabic-script name
// instead of a Latin string in an Arabic-script font fallback.
// Translations are short, playful adjectives + animal nouns; the
// generated name keeps adjective-adjective-animal order (same as the
// ES path). Some near-synonyms collide (e.g. brave ↔ courageous);
// alternative words are used where possible to keep variety.
const AR: Record<string, string> = {
  // ADJECTIVES_1
  brave: "شجاع", bold: "جريء", bright: "مشرق", calm: "هادئ",
  clever: "ذكي", cosmic: "كوني", cozy: "دافئ", daring: "مغامر",
  dancing: "راقص", dreamy: "حالم", eager: "متلهف",
  electric: "كهربائي", epic: "ملحمي", fearless: "جسور",
  fierce: "شرس", free: "حر", gentle: "لطيف", glad: "مسرور",
  glowing: "متوهج", golden: "ذهبي", grand: "فخم",
  happy: "سعيد", humble: "متواضع", keen: "حاد", kind: "طيب",
  lively: "حيوي", lucky: "محظوظ", loyal: "وفي", magic: "سحري",
  merry: "مرح", mighty: "قوي", noble: "نبيل", plucky: "مقدام",
  proud: "فخور", quick: "سريع", quiet: "ساكن", rad: "رائع",
  ready: "جاهز", rising: "صاعد", roaming: "متجول",
  shining: "لامع", smooth: "ناعم", snappy: "نشيط",
  soaring: "محلق", sparky: "متألق", speedy: "خاطف",
  spirited: "حماسي", steady: "ثابت", stellar: "نجمي",
  stoked: "متحمس",

  // ADJECTIVES_2
  agile: "رشيق", awesome: "مذهل", breezy: "منعش", chill: "مسترخي",
  clear: "صاف", crisp: "مقرمش", curious: "فضولي", dapper: "أنيق",
  deft: "ماهر", earnest: "جاد", fair: "عادل", fancy: "فاخر",
  fleet: "خفيف", fluffy: "ريشي", focused: "مركز",
  fresh: "طازج", frisky: "لعوب", fun: "ممتع",
  fuzzy: "فروي", groovy: "هادئ", gutsy: "جسور", handy: "بارع",
  hearty: "ودود", honest: "صادق", jazzy: "زاهي",
  joyful: "مبتهج", jumpy: "قافز", legit: "أصيل",
  nimble: "خفيف", nifty: "بارع", peppy: "نشط", perky: "بشوش",
  plush: "وثير", polished: "مصقول", prime: "ممتاز",
  pumped: "متحمس", quirky: "غريب", rare: "نادر",
  real: "حقيقي", robust: "متين", savvy: "داهية", sharp: "حاد",
  slick: "سلس", snug: "مريح", solid: "صلب", spry: "نشط",
  sure: "واثق", swift: "سريع", true: "صادق", vivid: "زاهي",

  // ANIMALS
  bear: "دب", bunny: "أرنب", turtle: "سلحفاة",
  chipmunk: "سنجاب", fox: "ثعلب", owl: "بومة",
  penguin: "بطريق", cat: "قط",
};

const TABLES: Partial<Record<AppLocale, Record<string, string>>> = {
  es: ES,
  ar: AR,
};

/**
 * Translates a generated character name (e.g., "Ready Jazzy Fox") into
 * the active locale by word-by-word substitution. Word order is
 * preserved — the generated name is a playful triplet, not formal
 * prose, so `Listo Llamativo Zorro` / `جاهز زاهي ثعلب` reads naturally
 * enough in target locales without per-locale grammar rules.
 *
 * Falls through to the original name for English (no table) and for
 * any individual word not in the locale's dictionary (e.g., a custom
 * name typed by the user).
 */
export function localizeProfileName(
  name: string,
  locale: AppLocale,
): string {
  const table = TABLES[locale];
  if (!table) return name;
  return name
    .split(" ")
    .map((word) => {
      const stripped = word.replace(/\d+$/, "");
      const digits = word.slice(stripped.length);
      const translated = table[stripped.toLowerCase()];
      return translated ? translated + digits : word;
    })
    .join(" ");
}
