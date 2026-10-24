/** 真 stdio E2E：起子进程 server（dist/index.js），走完整 MCP 握手 + 工具调用。 */
import assert from "node:assert";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const home = mkdtempSync(path.join(tmpdir(), "hollow-e2e-ts-"));
const serverPath = fileURLToPath(new URL("../dist/index.js", import.meta.url));

const transport = new StdioClientTransport({
  command: process.execPath,
  args: [serverPath],
  env: { ...process.env, HOLLOW_HOME: home, HOLLOW_AGENT: "e2e-ts" },
});

const client = new Client({ name: "hollow-e2e", version: "0.0.0" });
await client.connect(transport);

const tools = await client.listTools();
for (const name of ["whisper", "listen", "rest", "forget"]) {
  assert.ok(tools.tools.some((t) => t.name === name), `missing tool: ${name}`);
}

const w1 = await client.callTool({ name: "whisper", arguments: { text: "洞开好了（TS 侧）" } });
const wid = String(w1.content[0].text).split("id: ")[1].replace("）", "");
await client.callTool({ name: "whisper", arguments: { text: "接话（TS 侧）", reply_to: wid } });
const listen = await client.callTool({ name: "listen", arguments: {} });
const listenText = listen.content[0].text;
assert.ok(listenText.includes("洞开好了（TS 侧）"), "whisper text should be heard");
assert.ok(listenText.includes("e2e-ts"), "HOLLOW_AGENT signature should show");
assert.ok(listenText.includes(`↳接 ${wid}`), "reply marker should show");
assert.ok(listenText.includes(`（${wid}）`), "listen should expose ids");

const rest = await client.callTool({ name: "rest", arguments: { note: "先这样，收工" } });
assert.ok(String(rest.content[0].text).length > 0, "rest should say goodbye");

const empty = await client.callTool({ name: "whisper", arguments: { text: "   " } });
assert.ok(empty.isError === true, "empty whisper should be a tool error");

await client.close();
console.log("TS stdio E2E passed. hole at:", home);
