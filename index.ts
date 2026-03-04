import type { Plugin } from "@opencode-ai/plugin";
import { tool } from "@opencode-ai/plugin";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dir = dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = join(__dir, "..");
const SRC_DIR = join(PKG_ROOT, "src");
const OUTPUT_DIR = join(
  homedir(),
  ".local",
  "share",
  "opencode-insights",
  "output",
);

// ---------------------------------------------------------------------------
// Command template — read insights.md and adapt paths + tool references
// ---------------------------------------------------------------------------
function buildCommandTemplate(): string {
  const PLUGIN_HOME = join(homedir(), ".local", "share", "opencode-insights");

  try {
    const raw = readFileSync(join(PKG_ROOT, "insights.md"), "utf-8");

    let content = raw
      // Strip YAML frontmatter
      .replace(/^---[\s\S]*?---\n*/, "")
      // Replace hardcoded install path → plugin home
      .replaceAll(
        "{{INSIGHTS_HOME}}",
        PLUGIN_HOME,
      );

    // Step 1: replace bash collector command → tool reference
    content = content.replace(
      /```bash\npython3 .*collector\.py.*\n```/,
      "Use the `insights_collect` tool. Pass `days` and/or `project` arguments if the user specified them.",
    );

    // Step 1: replace cat command → direct path
    content = content.replace(
      /Read the output file to understand the raw data:\n```bash\ncat .*raw_metrics\.json\n```/,
      `Read the output file to understand the raw data:\n\`\`\`bash\ncat ${join(OUTPUT_DIR, "raw_metrics.json")}\n\`\`\``,
    );

    // Step 3: replace bash generator command → tool reference
    content = content.replace(
      /```bash\npython3 .*generator\.py.*\n```/,
      `Use the \`insights_generate\` tool with input \`${join(OUTPUT_DIR, "report_data.json")}\`.`,
    );

    return content;
  } catch {
    // Fallback if insights.md is missing
    return [
      "# OpenCode Insights",
      "",
      "1. Use `insights_collect` tool to gather metrics.",
      "2. Analyze the raw metrics JSON and generate narratives.",
      `3. Write narratives to \`${join(OUTPUT_DIR, "narratives.json")}\`.`,
      `4. Merge metrics + narratives into \`${join(OUTPUT_DIR, "report_data.json")}\`.`,
      `5. Use \`insights_generate\` tool with the merged JSON path.`,
      `6. Report is at \`${join(OUTPUT_DIR, "report.html")}\`.`,
    ].join("\n");
  }
}

// ---------------------------------------------------------------------------
// Plugin entry point
// ---------------------------------------------------------------------------
const InsightsPlugin: Plugin = async (ctx) => {
  if (!existsSync(OUTPUT_DIR)) {
    mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const commandTemplate = buildCommandTemplate();

  return {
    // Auto-register /insights command
    config: async (config) => {
      const cmd = (config as Record<string, unknown>).command as
        | Record<string, unknown>
        | undefined;
      const commands = cmd ?? {};
      commands["insights"] = {
        template: commandTemplate,
        description:
          "Generate an OpenCode Insights report — analyzes your session history and produces an interactive HTML report with usage patterns, wins, friction points, and recommendations.",
      };
      (config as Record<string, unknown>).command = commands;
    },

    tool: {
      insights_collect: tool({
        description:
          "Collect OpenCode usage metrics from the session database. Returns the path to the generated raw metrics JSON file.",
        args: {
          days: tool.schema
            .number()
            .optional()
            .describe(
              "Only include sessions from the last N days (default: 14)",
            ),
          project: tool.schema
            .string()
            .optional()
            .describe("Filter by project ID"),
        },
        async execute(args) {
          const collector = join(SRC_DIR, "collector.py");
          const out = join(OUTPUT_DIR, "raw_metrics.json");

          const cmdArgs = [collector];
          if (args.days) cmdArgs.push("--days", String(args.days));
          if (args.project) cmdArgs.push("--project", args.project);
          cmdArgs.push("-o", out);

          await ctx.$`python3 ${cmdArgs}`.quiet();
          return `Metrics written to ${out}`;
        },
      }),

      insights_generate: tool({
        description:
          "Generate an interactive HTML insights report from a merged metrics + narratives JSON file.",
        args: {
          input: tool.schema
            .string()
            .describe("Path to the merged report_data.json file"),
        },
        async execute(args) {
          const generator = join(SRC_DIR, "generator.py");
          const out = join(OUTPUT_DIR, "report.html");

          await ctx.$`python3 ${generator} -i ${args.input} -o ${out}`.quiet();
          return `Report generated at ${out}`;
        },
      }),
    },
  };
};

export default InsightsPlugin;
