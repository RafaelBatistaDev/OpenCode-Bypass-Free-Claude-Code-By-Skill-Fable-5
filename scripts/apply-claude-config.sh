bun -e '
import os from "node:os";
import path from "node:path";

const configPath = path.join(os.homedir(), ".claude.json");
const file = Bun.file(configPath);
const json = await file.json();

json.primaryApiKey = "sk-bypass";
json.openRouterApiKey = "sk-bypass";

if (json.clientDataCacheSlots) {
    for (const key of Object.keys(json.clientDataCacheSlots)) {
        json.clientDataCacheSlots[key].model = "deepseek-v4-flash-free";
    }
}

json.additionalModelOptionsCache = [
    { value: "deepseek-v4-flash-free", label: "DeepSeek V4 Flash Free", description: "DeepSeek flash free model with reasoning" },
    { value: "ling-3.0-flash-free", label: "Ling 3.0 Flash Free", description: "Ling flash free model with reasoning" },
    { value: "north-mini-code-free", label: "North Mini Code Free", description: "North mini code free model" },
];

await Bun.write(configPath, JSON.stringify(json, null, 2));
console.info("Configuracao do Claude atualizada com sucesso!");
'