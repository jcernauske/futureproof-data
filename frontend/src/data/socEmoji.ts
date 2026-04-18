// SOC major-group emoji mapping. The backend does not ship an emoji field on
// CareerOutcome, so the frontend derives one from the first two digits of the
// SOC code (the BLS "major group"). Unknown groups fall back to a neutral 💼.

const SOC_MAJOR_GROUP_EMOJI: Record<string, string> = {
  "11": "🧭", // Management
  "13": "📊", // Business & Financial
  "15": "💻", // Computer & Mathematical
  "17": "🛠️", // Architecture & Engineering
  "19": "🔬", // Life, Physical, Social Science
  "21": "🤝", // Community & Social Service
  "23": "⚖️", // Legal
  "25": "📚", // Education
  "27": "🎨", // Arts, Design, Entertainment, Sports, Media
  "29": "🩺", // Healthcare Practitioners
  "31": "🏥", // Healthcare Support
  "33": "🛡️", // Protective Service
  "35": "🍳", // Food Preparation & Serving
  "37": "🧹", // Building & Grounds Cleaning
  "39": "💇", // Personal Care & Service
  "41": "🛍️", // Sales & Related
  "43": "📋", // Office & Administrative Support
  "45": "🌾", // Farming, Fishing, Forestry
  "47": "🏗️", // Construction & Extraction
  "49": "🔧", // Installation, Maintenance, Repair
  "51": "🏭", // Production
  "53": "🚚", // Transportation & Material Moving
  "55": "🎖️", // Military Specific
};

export function socEmoji(socCode: string | null | undefined): string {
  if (!socCode) return "💼";
  const prefix = socCode.slice(0, 2);
  return SOC_MAJOR_GROUP_EMOJI[prefix] ?? "💼";
}
