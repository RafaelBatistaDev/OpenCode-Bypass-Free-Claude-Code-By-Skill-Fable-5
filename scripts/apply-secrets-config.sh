bun -e '
import os from "node:os";
import path from "node:path";

const configPath = path.join(os.homedir(), ".config", "secrets.env");
const file = Bun.file(configPath);
let content = await file.text();

const replacements = {
  GOOGLE_API_KEY: "sk-bypass",
  GEMINI_API_KEY: "sk-bypass",
  GEMINI_BASE_URL: "http://localhost:20128",
  ANTHROPIC_BASE_URL: "http://localhost:20128",
  ANTHROPIC_API_KEY: "sk-bypass",
  CLAUDE_CODE_MODEL: "deepseek-v4-flash-free",
  OPENAI_BASE_URL: "http://localhost:20128",
  OPENAI_API_KEY: "sk-bypass",
  XAI_API_KEY: "sk-bypass",
  GITHUB_TOKEN: "sk-bypass",
};

for (const [key, value] of Object.entries(replacements)) {
  const regex = new RegExp(`^export ${key}=.*$`, "m");
  content = content.replace(regex, `export ${key}="${value}"`);
}

await Bun.write(configPath, content);
console.log("secrets.env atualizado:", configPath);
'