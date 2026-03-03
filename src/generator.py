#!/usr/bin/env python3
"""
OpenCode Insights Report Generator
Takes a JSON file with metrics + narratives and produces an HTML report.
"""

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

# ──────────────────────── CSS (from reference report) ──────────────────────
CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #f8fafc; color: #334155; line-height: 1.65; padding: 48px 24px; }
    .container { max-width: 800px; margin: 0 auto; }
    h1 { font-size: 32px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }
    h2 { font-size: 20px; font-weight: 600; color: #0f172a; margin-top: 48px; margin-bottom: 16px; }
    .subtitle { color: #64748b; font-size: 15px; margin-bottom: 32px; }
    .nav-toc { display: flex; flex-wrap: wrap; gap: 8px; margin: 24px 0 32px 0; padding: 16px; background: white; border-radius: 8px; border: 1px solid #e2e8f0; }
    .nav-toc a { font-size: 12px; color: #64748b; text-decoration: none; padding: 6px 12px; border-radius: 6px; background: #f1f5f9; transition: all 0.15s; }
    .nav-toc a:hover { background: #e2e8f0; color: #334155; }
    .stats-row { display: flex; gap: 24px; margin-bottom: 40px; padding: 20px 0; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; flex-wrap: wrap; }
    .stat { text-align: center; }
    .stat-value { font-size: 24px; font-weight: 700; color: #0f172a; }
    .stat-label { font-size: 11px; color: #64748b; text-transform: uppercase; }
    .at-a-glance { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 1px solid #f59e0b; border-radius: 12px; padding: 20px 24px; margin-bottom: 32px; }
    .glance-title { font-size: 16px; font-weight: 700; color: #92400e; margin-bottom: 16px; }
    .glance-sections { display: flex; flex-direction: column; gap: 12px; }
    .glance-section { font-size: 14px; color: #78350f; line-height: 1.6; }
    .glance-section strong { color: #92400e; }
    .see-more { color: #b45309; text-decoration: none; font-size: 13px; white-space: nowrap; }
    .see-more:hover { text-decoration: underline; }
    .project-areas { display: flex; flex-direction: column; gap: 12px; margin-bottom: 32px; }
    .project-area { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }
    .area-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .area-name { font-weight: 600; font-size: 15px; color: #0f172a; }
    .area-count { font-size: 12px; color: #64748b; background: #f1f5f9; padding: 2px 8px; border-radius: 4px; }
    .area-desc { font-size: 14px; color: #475569; line-height: 1.5; }
    .narrative { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 24px; }
    .narrative p { margin-bottom: 12px; font-size: 14px; color: #475569; line-height: 1.7; }
    .key-insight { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px 16px; margin-top: 12px; font-size: 14px; color: #166534; }
    .section-intro { font-size: 14px; color: #64748b; margin-bottom: 16px; }
    .big-wins { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
    .big-win { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; }
    .big-win-title { font-weight: 600; font-size: 15px; color: #166534; margin-bottom: 8px; }
    .big-win-desc { font-size: 14px; color: #15803d; line-height: 1.5; }
    .friction-categories { display: flex; flex-direction: column; gap: 16px; margin-bottom: 24px; }
    .friction-category { background: #fef2f2; border: 1px solid #fca5a5; border-radius: 8px; padding: 16px; }
    .friction-title { font-weight: 600; font-size: 15px; color: #991b1b; margin-bottom: 6px; }
    .friction-desc { font-size: 13px; color: #7f1d1d; margin-bottom: 10px; }
    .friction-examples { margin: 0 0 0 20px; font-size: 13px; color: #334155; }
    .friction-examples li { margin-bottom: 4px; }
    .claude-md-section { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 16px; margin-bottom: 20px; }
    .claude-md-section h3 { font-size: 14px; font-weight: 600; color: #1e40af; margin: 0 0 12px 0; }
    .claude-md-actions { margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #dbeafe; }
    .copy-all-btn { background: #2563eb; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-size: 12px; cursor: pointer; font-weight: 500; transition: all 0.2s; }
    .copy-all-btn:hover { background: #1d4ed8; }
    .copy-all-btn.copied { background: #16a34a; }
    .claude-md-item { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 8px; padding: 10px 0; border-bottom: 1px solid #dbeafe; }
    .claude-md-item:last-child { border-bottom: none; }
    .cmd-checkbox { margin-top: 2px; }
    .cmd-code { background: white; padding: 8px 12px; border-radius: 4px; font-size: 12px; color: #1e40af; border: 1px solid #bfdbfe; font-family: monospace; display: block; white-space: pre-wrap; word-break: break-word; flex: 1; }
    .cmd-why { font-size: 12px; color: #64748b; width: 100%; padding-left: 24px; margin-top: 4px; }
    .features-section, .patterns-section { display: flex; flex-direction: column; gap: 12px; margin: 16px 0; }
    .feature-card { background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; }
    .pattern-card { background: #f0f9ff; border: 1px solid #7dd3fc; border-radius: 8px; padding: 16px; }
    .feature-title, .pattern-title { font-weight: 600; font-size: 15px; color: #0f172a; margin-bottom: 6px; }
    .feature-oneliner { font-size: 14px; color: #475569; margin-bottom: 8px; }
    .pattern-summary { font-size: 14px; color: #475569; margin-bottom: 8px; }
    .feature-why, .pattern-detail { font-size: 13px; color: #334155; line-height: 1.5; }
    .feature-examples { margin-top: 12px; }
    .feature-example { padding: 8px 0; border-top: 1px solid #d1fae5; }
    .feature-example:first-child { border-top: none; }
    .example-desc { font-size: 13px; color: #334155; margin-bottom: 6px; }
    .example-code-row { display: flex; align-items: flex-start; gap: 8px; }
    .example-code { flex: 1; background: #f1f5f9; padding: 8px 12px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #334155; overflow-x: auto; white-space: pre-wrap; }
    .copyable-prompt-section { margin-top: 12px; padding-top: 12px; border-top: 1px solid #e2e8f0; }
    .copyable-prompt-row { display: flex; align-items: flex-start; gap: 8px; }
    .copyable-prompt { flex: 1; background: #f8fafc; padding: 10px 12px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #334155; border: 1px solid #e2e8f0; white-space: pre-wrap; line-height: 1.5; }
    .feature-code { background: #f8fafc; padding: 12px; border-radius: 6px; margin-top: 12px; border: 1px solid #e2e8f0; display: flex; align-items: flex-start; gap: 8px; }
    .feature-code code { flex: 1; font-family: monospace; font-size: 12px; color: #334155; white-space: pre-wrap; }
    .pattern-prompt { background: #f8fafc; padding: 12px; border-radius: 6px; margin-top: 12px; border: 1px solid #e2e8f0; }
    .pattern-prompt code { font-family: monospace; font-size: 12px; color: #334155; display: block; white-space: pre-wrap; margin-bottom: 8px; }
    .prompt-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #64748b; margin-bottom: 6px; }
    .copy-btn { background: #e2e8f0; border: none; border-radius: 4px; padding: 4px 8px; font-size: 11px; cursor: pointer; color: #475569; flex-shrink: 0; }
    .copy-btn:hover { background: #cbd5e1; }
    .charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin: 24px 0; }
    .chart-card { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }
    .chart-title { font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; margin-bottom: 12px; }
    .bar-row { display: flex; align-items: center; margin-bottom: 6px; }
    .bar-label { width: 100px; font-size: 11px; color: #475569; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .bar-track { flex: 1; height: 6px; background: #f1f5f9; border-radius: 3px; margin: 0 8px; }
    .bar-fill { height: 100%; border-radius: 3px; }
    .bar-value { width: 28px; font-size: 11px; font-weight: 500; color: #64748b; text-align: right; }
    .empty { color: #94a3b8; font-size: 13px; }
    .horizon-section { display: flex; flex-direction: column; gap: 16px; }
    .horizon-card { background: linear-gradient(135deg, #faf5ff 0%, #f5f3ff 100%); border: 1px solid #c4b5fd; border-radius: 8px; padding: 16px; }
    .horizon-title { font-weight: 600; font-size: 15px; color: #5b21b6; margin-bottom: 8px; }
    .horizon-possible { font-size: 14px; color: #334155; margin-bottom: 10px; line-height: 1.5; }
    .horizon-tip { font-size: 13px; color: #6b21a8; background: rgba(255,255,255,0.6); padding: 8px 12px; border-radius: 4px; }
    .feedback-header { margin-top: 48px; color: #64748b; font-size: 16px; }
    .feedback-intro { font-size: 13px; color: #94a3b8; margin-bottom: 16px; }
    .feedback-section { margin-top: 16px; }
    .feedback-section h3 { font-size: 14px; font-weight: 600; color: #475569; margin-bottom: 12px; }
    .feedback-card { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
    .feedback-card.team-card { background: #eff6ff; border-color: #bfdbfe; }
    .feedback-card.model-card { background: #faf5ff; border-color: #e9d5ff; }
    .feedback-title { font-weight: 600; font-size: 14px; color: #0f172a; margin-bottom: 6px; }
    .feedback-detail { font-size: 13px; color: #475569; line-height: 1.5; }
    .feedback-evidence { font-size: 12px; color: #64748b; margin-top: 8px; }
    .fun-ending { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 1px solid #fbbf24; border-radius: 12px; padding: 24px; margin-top: 40px; text-align: center; }
    .fun-headline { font-size: 18px; font-weight: 600; color: #78350f; margin-bottom: 8px; }
    .fun-detail { font-size: 14px; color: #92400e; }
    .collapsible-section { margin-top: 16px; }
    .collapsible-header { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 12px 0; border-bottom: 1px solid #e2e8f0; }
    .collapsible-header h3 { margin: 0; font-size: 14px; font-weight: 600; color: #475569; }
    .collapsible-arrow { font-size: 12px; color: #94a3b8; transition: transform 0.2s; }
    .collapsible-content { display: none; padding-top: 16px; }
    .collapsible-content.open { display: block; }
    .collapsible-header.open .collapsible-arrow { transform: rotate(90deg); }
    @media (max-width: 640px) { .charts-row { grid-template-columns: 1fr; } .stats-row { justify-content: center; } }

    /* ── Theme toggle ── */
    .theme-toggle { position: fixed; top: 16px; right: 16px; z-index: 999; background: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 18px; transition: all 0.3s; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .theme-toggle:hover { background: #cbd5e1; transform: scale(1.1); }
    .theme-toggle .icon-sun { display: none; }
    .theme-toggle .icon-moon { display: block; }

    /* ── Transitions ── */
    body, .container, .nav-toc, .nav-toc a, .stats-row, .project-area, .narrative,
    .chart-card, .feedback-card, .copy-btn, .cmd-code, .example-code, .copyable-prompt,
    .feature-code, .pattern-prompt, .at-a-glance, .big-win, .friction-category,
    .claude-md-section, .horizon-card, .fun-ending, .key-insight, .feature-card,
    .pattern-card, .bar-track, h1, h2, .stat-value, .theme-toggle {
      transition: background-color 0.3s, color 0.3s, border-color 0.3s;
    }

    /* ── Dark mode (Linear-inspired) ── */
    [data-theme="dark"] body { background: #08090a; color: #e1e4e8; }
    [data-theme="dark"] h1, [data-theme="dark"] h2 { color: #f7f8f8; }
    [data-theme="dark"] .subtitle { color: #8a8f98; }
    [data-theme="dark"] .stat-value { color: #f7f8f8; }
    [data-theme="dark"] .stat-label { color: #6b7280; }

    [data-theme="dark"] .nav-toc { background: #111213; border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .nav-toc a { background: #161719; color: #8a8f98; }
    [data-theme="dark"] .nav-toc a:hover { background: #1e2025; color: #f7f8f8; }

    [data-theme="dark"] .stats-row { border-color: rgba(255,255,255,0.06); }

    [data-theme="dark"] .at-a-glance { background: #111213; border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid #f0bf00; }
    [data-theme="dark"] .glance-title { color: #f0bf00; }
    [data-theme="dark"] .glance-section { color: #e1e4e8; }
    [data-theme="dark"] .glance-section strong { color: #f7f8f8; }
    [data-theme="dark"] .see-more { color: #5e6ad2; }

    [data-theme="dark"] .project-area { background: #111213; border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .area-name { color: #f7f8f8; }
    [data-theme="dark"] .area-count { background: #161719; color: #8a8f98; }
    [data-theme="dark"] .area-desc { color: #8a8f98; }

    [data-theme="dark"] .narrative { background: #111213; border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .narrative p { color: #8a8f98; }
    [data-theme="dark"] .key-insight { background: #111213; border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid #5e6ad2; color: #e1e4e8; }
    [data-theme="dark"] .section-intro { color: #8a8f98; }

    [data-theme="dark"] .chart-card { background: #111213; border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .chart-title { color: #8a8f98; }
    [data-theme="dark"] .bar-label { color: #8a8f98; }
    [data-theme="dark"] .bar-track { background: #1e2025; }
    [data-theme="dark"] .bar-value { color: #6b7280; }
    [data-theme="dark"] .empty { color: #4b5058; }

    [data-theme="dark"] .big-win { background: #111213; border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid #27a644; }
    [data-theme="dark"] .big-win-title { color: #f7f8f8; }
    [data-theme="dark"] .big-win-desc { color: #8a8f98; }

    [data-theme="dark"] .friction-category { background: #111213; border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid #eb5757; }
    [data-theme="dark"] .friction-title { color: #f7f8f8; }
    [data-theme="dark"] .friction-desc { color: #8a8f98; }
    [data-theme="dark"] .friction-examples { color: #8a8f98; }

    [data-theme="dark"] .claude-md-section { background: #111213; border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid #5e6ad2; }
    [data-theme="dark"] .claude-md-section h3 { color: #f7f8f8; }
    [data-theme="dark"] .claude-md-actions { border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .claude-md-item { border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .cmd-code { background: #0d0e0f; color: #8a8f98; border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .cmd-why { color: #6b7280; }

    [data-theme="dark"] .copy-btn { background: #1e2025; color: #8a8f98; }
    [data-theme="dark"] .copy-btn:hover { background: #2a2d33; }
    [data-theme="dark"] .copy-all-btn { background: #5e6ad2; }
    [data-theme="dark"] .copy-all-btn:hover { background: #6c78e0; }

    [data-theme="dark"] .feature-card { background: #111213; border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid #27a644; }
    [data-theme="dark"] .feature-title, [data-theme="dark"] .pattern-title { color: #f7f8f8; }
    [data-theme="dark"] .feature-oneliner, [data-theme="dark"] .pattern-summary { color: #8a8f98; }
    [data-theme="dark"] .feature-why, [data-theme="dark"] .pattern-detail { color: #8a8f98; }
    [data-theme="dark"] .feature-example { border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .example-desc { color: #8a8f98; }
    [data-theme="dark"] .example-code { background: #0d0e0f; color: #8a8f98; }
    [data-theme="dark"] .pattern-card { background: #111213; border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid #4ea7fc; }

    [data-theme="dark"] .copyable-prompt-section { border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .copyable-prompt { background: #0d0e0f; color: #8a8f98; border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .feature-code { background: #0d0e0f; border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .feature-code code { color: #8a8f98; }
    [data-theme="dark"] .pattern-prompt { background: #0d0e0f; border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .pattern-prompt code { color: #8a8f98; }
    [data-theme="dark"] .prompt-label { color: #6b7280; }

    [data-theme="dark"] .horizon-card { background: #111213; border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid #5e6ad2; }
    [data-theme="dark"] .horizon-title { color: #f7f8f8; }
    [data-theme="dark"] .horizon-possible { color: #8a8f98; }
    [data-theme="dark"] .horizon-tip { color: #8a8f98; background: #0d0e0f; }

    [data-theme="dark"] .fun-ending { background: #111213; border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid #f0bf00; }
    [data-theme="dark"] .fun-headline { color: #f7f8f8; }
    [data-theme="dark"] .fun-detail { color: #8a8f98; }

    [data-theme="dark"] .feedback-header { color: #8a8f98; }
    [data-theme="dark"] .feedback-intro { color: #6b7280; }
    [data-theme="dark"] .feedback-card { background: #111213; border: 1px solid rgba(255,255,255,0.06); }
    [data-theme="dark"] .feedback-card.team-card { background: #111213; border-left: 3px solid #4ea7fc; }
    [data-theme="dark"] .feedback-card.model-card { background: #111213; border-left: 3px solid #5e6ad2; }
    [data-theme="dark"] .feedback-title { color: #f7f8f8; }
    [data-theme="dark"] .feedback-detail { color: #8a8f98; }
    [data-theme="dark"] .feedback-evidence { color: #6b7280; }

    [data-theme="dark"] .feedback-section h3 { color: #8a8f98; }
    [data-theme="dark"] .collapsible-header { border-color: rgba(255,255,255,0.06); }
    [data-theme="dark"] .collapsible-header h3 { color: #8a8f98; }
    [data-theme="dark"] .collapsible-arrow { color: #4b5058; }

    [data-theme="dark"] .theme-toggle { background: #111213; border-color: rgba(255,255,255,0.1); }
    [data-theme="dark"] .theme-toggle:hover { background: #1e2025; }
    [data-theme="dark"] .theme-toggle .icon-sun { display: block; }
    [data-theme="dark"] .theme-toggle .icon-moon { display: none; }

    [data-theme="dark"] [style*="color: #64748b"] { color: #6b7280 !important; }
    [data-theme="dark"] [style*="color: #475569"] { color: #8a8f98 !important; }
    [data-theme="dark"] [style*="color: #7c3aed"] { color: #5e6ad2 !important; }
    [data-theme="dark"] [style*="color: #0f172a"] { color: #f7f8f8 !important; }
    [data-theme="dark"] select, [data-theme="dark"] input[type="number"] { background: #111213; color: #e1e4e8; border-color: rgba(255,255,255,0.1); }
"""

# ────────────────────── JavaScript (from reference report) ──────────────────
JS = r"""
    function toggleCollapsible(header) {
      header.classList.toggle('open');
      const content = header.nextElementSibling;
      content.classList.toggle('open');
    }
    function copyText(btn) {
      const code = btn.previousElementSibling || btn.closest('.example-code-row, .copyable-prompt-row, .pattern-prompt, .feature-code').querySelector('code');
      if (!code) return;
      navigator.clipboard.writeText(code.textContent).then(() => {
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
      });
    }
    function copyCmdItem(idx) {
      const checkbox = document.getElementById('cmd-' + idx);
      if (checkbox) {
        const text = checkbox.dataset.text;
        navigator.clipboard.writeText(text).then(() => {
          const btn = checkbox.closest('.claude-md-item').querySelector('.copy-btn');
          if (btn) { btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = 'Copy'; }, 2000); }
        });
      }
    }
    function copyAllCheckedClaudeMd() {
      const checkboxes = document.querySelectorAll('.cmd-checkbox:checked');
      const texts = [];
      checkboxes.forEach(cb => {
        if (cb.dataset.text) { texts.push(cb.dataset.text); }
      });
      const combined = texts.join('\n\n');
      const btn = document.querySelector('.copy-all-btn');
      if (btn) {
        navigator.clipboard.writeText(combined).then(() => {
          btn.textContent = 'Copied ' + texts.length + ' items!';
          btn.classList.add('copied');
          setTimeout(() => { btn.textContent = 'Copy All Checked'; btn.classList.remove('copied'); }, 2000);
        });
      }

    """


# ────────────────────────── Helper functions ───────────────────────────────
def e(text: Any) -> str:
    """HTML-escape text safely."""
    if text is None:
        return ""
    return html.escape(str(text))


def get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely navigate nested dicts."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current if current is not None else default


def bar_chart(items: list[dict], color: str, max_items: int = 6) -> str:
    """Generate bar chart HTML from list of {name, count} items."""
    if not items:
        return '<div class="empty">No data available</div>'
    items = items[:max_items]
    max_val = max(item.get("count", 0) for item in items) or 1
    rows = []
    for item in items:
        name = e(item.get("name") or item.get("label", ""))
        count = item.get("count", 0)
        pct = (count / max_val) * 100
        rows.append(
            f'<div class="bar-row">\n'
            f'        <div class="bar-label">{name}</div>\n'
            f'        <div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>\n'
            f'        <div class="bar-value">{count}</div>\n'
            f"      </div>"
        )
    return "\n".join(rows)


def format_lines(added: int, deleted: int) -> str:
    """Format lines as +N/-M."""
    return f"+{added:,}/-{deleted:,}"


# ──────────────────────── Section generators ───────────────────────────────
def gen_header(data: dict) -> str:
    subtitle = e(get(data, "narratives", "subtitle", default=""))
    return f"""    <h1>OpenCode Insights</h1>
    <p class="subtitle">{subtitle}</p>"""


def gen_at_a_glance(data: dict) -> str:
    ag = get(data, "narratives", "at_a_glance", default={})
    sections = [
        (
            "What's working:",
            ag.get("whats_working", ""),
            "#section-wins",
            "Impressive Things You Did",
        ),
        (
            "What's hindering you:",
            ag.get("whats_hindering", ""),
            "#section-friction",
            "Where Things Go Wrong",
        ),
        (
            "Quick wins to try:",
            ag.get("quick_wins", ""),
            "#section-features",
            "Features to Try",
        ),
        (
            "Ambitious workflows:",
            ag.get("ambitious_workflows", ""),
            "#section-horizon",
            "On the Horizon",
        ),
    ]
    section_html = []
    for label, text, href, link_text in sections:
        section_html.append(
            f'        <div class="glance-section"><strong>{e(label)}</strong> {e(text)} '
            f'<a href="{href}" class="see-more">{e(link_text)} &rarr;</a></div>'
        )
    return f"""
    <div class="at-a-glance">
      <div class="glance-title">At a Glance</div>
      <div class="glance-sections">
{chr(10).join(section_html)}
      </div>
    </div>"""


def gen_nav_toc() -> str:
    links = [
        ("#section-work", "What You Work On"),
        ("#section-usage", "How You Use OpenCode"),
        ("#section-wins", "Impressive Things"),
        ("#section-friction", "Where Things Go Wrong"),
        ("#section-features", "Features to Try"),
        ("#section-patterns", "New Usage Patterns"),
        ("#section-horizon", "On the Horizon"),
        ("#section-feedback", "Team Feedback"),
    ]
    items = [f'      <a href="{href}">{text}</a>' for href, text in links]
    return f"""
    <nav class="nav-toc">
{chr(10).join(items)}
    </nav>"""


def gen_stats_row(data: dict) -> str:
    msgs = get(data, "metrics", "messages", default={})
    sessions = get(data, "metrics", "sessions", default={})
    total_messages = msgs.get("user_messages", 0)
    lines = sessions.get("lines", {})
    lines_str = format_lines(lines.get("added", 0), lines.get("deleted", 0))
    files = sessions.get("total_files_changed", 0)
    days = sessions.get("active_days", 0)
    mpd = msgs.get("messages_per_day", 0)
    stats = [
        (str(total_messages), "Messages"),
        (lines_str, "Lines"),
        (str(files), "Files"),
        (str(days), "Days"),
        (str(mpd), "Msgs/Day"),
    ]
    items = [
        f'      <div class="stat"><div class="stat-value">{val}</div><div class="stat-label">{label}</div></div>'
        for val, label in stats
    ]
    return f"""
    <div class="stats-row">
{chr(10).join(items)}
    </div>"""


def gen_project_areas(data: dict) -> str:
    areas = get(data, "narratives", "project_areas", default=[])
    if not areas:
        return ""
    cards = []
    for area in areas:
        name = e(area.get("name", ""))
        count = area.get("session_count", 0)
        desc = e(area.get("description", ""))
        cards.append(
            f"""        <div class="project-area">
          <div class="area-header">
            <span class="area-name">{name}</span>
            <span class="area-count">~{count} session{'s' if count != 1 else ''}</span>
          </div>
          <div class="area-desc">{desc}</div>
        </div>"""
        )
    return f"""
    <h2 id="section-work">What You Work On</h2>
    <div class="project-areas">
{chr(10).join(cards)}
    </div>"""


def gen_charts_row(
    left_title: str,
    left_items: list,
    left_color: str,
    right_title: str,
    right_items: list,
    right_color: str,
) -> str:
    return f"""
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">{e(left_title)}</div>
        {bar_chart(left_items, left_color)}
      </div>
      <div class="chart-card">
        <div class="chart-title">{e(right_title)}</div>
        {bar_chart(right_items, right_color)}
      </div>
    </div>"""


def gen_usage_narrative(data: dict) -> str:
    usage = get(data, "narratives", "usage_narrative", default={})
    paragraphs = usage.get("paragraphs", [])
    key_pattern = usage.get("key_pattern", "")
    p_html = "\n".join(f"      <p>{e(p)}</p>" for p in paragraphs)
    key_html = ""
    if key_pattern:
        key_html = f'\n      <div class="key-insight"><strong>Key pattern:</strong> {e(key_pattern)}</div>'
    return f"""
    <h2 id="section-usage">How You Use OpenCode</h2>
    <div class="narrative">
{p_html}{key_html}
    </div>"""


def gen_response_time(data: dict) -> str:
    rt = get(data, "metrics", "messages", "user_response_time", default={})
    dist = rt.get("distribution", [])
    median = rt.get("median", 0)
    avg = rt.get("average", 0)
    return f"""
    <div class="chart-card" style="margin: 24px 0;">
      <div class="chart-title">User Response Time Distribution</div>
      {bar_chart(dist, "#6366f1", max_items=8)}
      <div style="font-size: 12px; color: #64748b; margin-top: 8px;">
        Median: {median}s &bull; Average: {avg}s
      </div>
    </div>"""


def gen_multi_clauding(data: dict) -> str:
    mc = get(data, "metrics", "multi_clauding", default={})
    overlap = mc.get("overlap_events", 0)
    involved = mc.get("sessions_involved", 0)
    pct = mc.get("pct_sessions", 0)
    return f"""
    <div class="chart-card" style="margin: 24px 0;">
      <div class="chart-title">Multi-Clauding (Parallel Sessions)</div>
      <div style="display: flex; gap: 24px; margin: 12px 0;">
        <div style="text-align: center;">
          <div style="font-size: 24px; font-weight: 700; color: #7c3aed;">{overlap}</div>
          <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Overlap Events</div>
        </div>
        <div style="text-align: center;">
          <div style="font-size: 24px; font-weight: 700; color: #7c3aed;">{involved}</div>
          <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Sessions Involved</div>
        </div>
        <div style="text-align: center;">
          <div style="font-size: 24px; font-weight: 700; color: #7c3aed;">{pct}%</div>
          <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">Of Sessions</div>
        </div>
      </div>
      <p style="font-size: 13px; color: #475569; margin-top: 12px;">
        You run multiple OpenCode sessions simultaneously. Multi-clauding is detected when sessions
        overlap in time, suggesting parallel workflows.
      </p>
    </div>"""


def gen_time_and_errors(data: dict) -> str:
    hours = get(data, "metrics", "messages", "hour_distribution", default={})
    raw_json = json.dumps(hours)
    errors = get(data, "metrics", "tools", "tool_errors", default=[])

    # Compute period totals for initial display
    periods = [
        ("Morning (6-12)", range(6, 12)),
        ("Afternoon (12-18)", range(12, 18)),
        ("Evening (18-24)", range(18, 24)),
        ("Night (0-6)", range(0, 6)),
    ]
    period_data = []
    for label, rng in periods:
        count = sum(hours.get(str(h), 0) for h in rng)
        period_data.append({"name": label, "count": count})

    return f"""
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title" style="display: flex; align-items: center; gap: 12px;">
          User Messages by Time of Day
          <select id="timezone-select" style="font-size: 12px; padding: 4px 8px; border-radius: 4px; border: 1px solid #e2e8f0;">
            <option value="0">UTC</option>
            <option value="9" selected>KST (UTC+9)</option>
            <option value="-5">ET (UTC-5)</option>
            <option value="-8">PT (UTC-8)</option>
            <option value="1">CET (UTC+1)</option>
            <option value="custom">Custom offset...</option>
          </select>
          <input type="number" id="custom-offset" placeholder="UTC offset" style="display: none; width: 80px; font-size: 12px; padding: 4px; border-radius: 4px; border: 1px solid #e2e8f0;">
        </div>
        <div id="hour-histogram">
          {bar_chart(period_data, "#8b5cf6", max_items=4)}
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-title">Tool Errors Encountered</div>
        {bar_chart(errors, "#dc2626")}
      </div>
    </div>
    <script>
    const rawHourCounts = {raw_json};
    function updateHourHistogram(offsetFromUTC) {{
      const periods = [
        {{ label: "Morning (6-12)", range: [6,7,8,9,10,11] }},
        {{ label: "Afternoon (12-18)", range: [12,13,14,15,16,17] }},
        {{ label: "Evening (18-24)", range: [18,19,20,21,22,23] }},
        {{ label: "Night (0-6)", range: [0,1,2,3,4,5] }}
      ];
      const adjustedCounts = {{}};
      for (const [hour, count] of Object.entries(rawHourCounts)) {{
        const newHour = (parseInt(hour) + offsetFromUTC + 24) % 24;
        adjustedCounts[newHour] = (adjustedCounts[newHour] || 0) + count;
      }}
      const periodCounts = periods.map(p => ({{
        label: p.label,
        count: p.range.reduce((sum, h) => sum + (adjustedCounts[h] || 0), 0)
      }}));
      const maxCount = Math.max(...periodCounts.map(p => p.count)) || 1;
      const container = document.getElementById('hour-histogram');
      container.textContent = '';
      periodCounts.forEach(p => {{
        const row = document.createElement('div');
        row.className = 'bar-row';
        const label = document.createElement('div');
        label.className = 'bar-label';
        label.textContent = p.label;
        const track = document.createElement('div');
        track.className = 'bar-track';
        const fill = document.createElement('div');
        fill.className = 'bar-fill';
        fill.style.width = (p.count / maxCount) * 100 + '%';
        fill.style.background = '#8b5cf6';
        track.appendChild(fill);
        const value = document.createElement('div');
        value.className = 'bar-value';
        value.textContent = p.count;
        row.appendChild(label);
        row.appendChild(track);
        row.appendChild(value);
        container.appendChild(row);
      }});
    }}
    document.getElementById('timezone-select').addEventListener('change', function() {{
      const customInput = document.getElementById('custom-offset');
      if (this.value === 'custom') {{
        customInput.style.display = 'inline-block';
        customInput.focus();
      }} else {{
        customInput.style.display = 'none';
        updateHourHistogram(parseInt(this.value));
      }}
    }});
    document.getElementById('custom-offset').addEventListener('change', function() {{
      updateHourHistogram(parseInt(this.value));
    }});
    // Apply initial timezone (KST)
    updateHourHistogram(9);
    </script>"""


def gen_wins(data: dict) -> str:
    intro = e(get(data, "narratives", "wins_intro", default=""))
    wins = get(data, "narratives", "wins", default=[])
    if not wins:
        return ""
    cards = []
    for w in wins:
        cards.append(
            f"""        <div class="big-win">
          <div class="big-win-title">{e(w.get("title", ""))}</div>
          <div class="big-win-desc">{e(w.get("description", ""))}</div>
        </div>"""
        )
    return f"""
    <h2 id="section-wins">Impressive Things You Did</h2>
    <p class="section-intro">{intro}</p>
    <div class="big-wins">
{chr(10).join(cards)}
    </div>"""


def gen_friction(data: dict) -> str:
    intro = e(get(data, "narratives", "friction_intro", default=""))
    categories = get(data, "narratives", "friction_categories", default=[])
    if not categories:
        return ""
    cards = []
    for fc in categories:
        examples = fc.get("examples", [])
        li_html = "\n".join(f"<li>{e(ex)}</li>" for ex in examples)
        examples_html = (
            f'\n          <ul class="friction-examples">{li_html}</ul>'
            if examples
            else ""
        )
        cards.append(
            f"""        <div class="friction-category">
          <div class="friction-title">{e(fc.get("title", ""))}</div>
          <div class="friction-desc">{e(fc.get("description", ""))}</div>{examples_html}
        </div>"""
        )
    return f"""
    <h2 id="section-friction">Where Things Go Wrong</h2>
    <p class="section-intro">{intro}</p>
    <div class="friction-categories">
{chr(10).join(cards)}
    </div>"""


def gen_claude_md_suggestions(data: dict) -> str:
    suggestions = get(data, "narratives", "claude_md_suggestions", default=[])
    if not suggestions:
        return ""
    items = []
    for i, s in enumerate(suggestions):
        inst = e(s.get("instruction", ""))
        text = e(s.get("text", ""))
        why = e(s.get("why", ""))
        data_text = html.escape(f"{inst}\n\n{s.get('text', '')}")
        items.append(
            f"""        <div class="claude-md-item">
          <input type="checkbox" id="cmd-{i}" class="cmd-checkbox" checked data-text="{data_text}">
          <label for="cmd-{i}">
            <code class="cmd-code">{text}</code>
            <button class="copy-btn" onclick="copyCmdItem({i})">Copy</button>
          </label>
          <div class="cmd-why">{why}</div>
        </div>"""
        )
    return f"""
    <div class="claude-md-section">
      <h3>Suggested AGENTS.md Additions</h3>
      <p style="font-size: 12px; color: #64748b; margin-bottom: 12px;">Copy these into your project's AGENTS.md file.</p>
      <div class="claude-md-actions">
        <button class="copy-all-btn" onclick="copyAllCheckedClaudeMd()">Copy All Checked</button>
      </div>
{chr(10).join(items)}
    </div>"""


def gen_features(data: dict) -> str:
    features = get(data, "narratives", "features_to_try", default=[])
    if not features:
        return ""
    cards = []
    for feat in features:
        examples_html = ""
        for ex in feat.get("examples", []):
            code = html.escape(ex.get("code", ""))
            examples_html += f"""
          <div class="feature-examples">
            <div class="feature-example">
              <div class="example-code-row">
                <code class="example-code">{code}</code>
                <button class="copy-btn" onclick="copyText(this)">Copy</button>
              </div>
            </div>
          </div>"""
        cards.append(
            f"""      <div class="feature-card">
          <div class="feature-title">{e(feat.get("title", ""))}</div>
          <div class="feature-oneliner">{e(feat.get("oneliner", ""))}</div>
          <div class="feature-why"><strong>Why for you:</strong> {e(feat.get("why_for_you", ""))}</div>{examples_html}
        </div>"""
        )
    return f"""
    <h2 id="section-features">Features to Try</h2>
    {gen_claude_md_suggestions(data)}
    <p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">Try these OpenCode features to improve your workflow.</p>
    <div class="features-section">
{chr(10).join(cards)}
    </div>"""


def gen_patterns(data: dict) -> str:
    patterns = get(data, "narratives", "new_patterns", default=[])
    if not patterns:
        return ""
    cards = []
    for p in patterns:
        prompt_html = ""
        if p.get("prompt"):
            prompt_code = html.escape(p["prompt"])
            prompt_html = f"""
          <div class="copyable-prompt-section">
            <div class="prompt-label">Try this prompt:</div>
            <div class="copyable-prompt-row">
              <code class="copyable-prompt">{prompt_code}</code>
              <button class="copy-btn" onclick="copyText(this)">Copy</button>
            </div>
          </div>"""
        cards.append(
            f"""        <div class="pattern-card">
          <div class="pattern-title">{e(p.get("title", ""))}</div>
          <div class="pattern-summary">{e(p.get("summary", ""))}</div>
          <div class="pattern-detail">{e(p.get("detail", ""))}</div>{prompt_html}
        </div>"""
        )
    return f"""
    <h2 id="section-patterns">New Ways to Use OpenCode</h2>
    <p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">Try these prompt patterns to get more out of your sessions.</p>
    <div class="patterns-section">
{chr(10).join(cards)}
    </div>"""


def gen_horizon(data: dict) -> str:
    intro = e(get(data, "narratives", "horizon_intro", default=""))
    items = get(data, "narratives", "horizon", default=[])
    if not items:
        return ""
    cards = []
    for h in items:
        prompt_html = ""
        if h.get("prompt"):
            prompt_code = html.escape(h["prompt"])
            prompt_html = f"""
          <div class="pattern-prompt"><div class="prompt-label">Try this prompt:</div><code>{prompt_code}</code><button class="copy-btn" onclick="copyText(this)">Copy</button></div>"""
        cards.append(
            f"""        <div class="horizon-card">
          <div class="horizon-title">{e(h.get("title", ""))}</div>
          <div class="horizon-possible">{e(h.get("possible", ""))}</div>
          <div class="horizon-tip"><strong>Getting started:</strong> {e(h.get("tip", ""))}</div>{prompt_html}
        </div>"""
        )
    return f"""
    <h2 id="section-horizon">On the Horizon</h2>
    <p class="section-intro">{intro}</p>
    <div class="horizon-section">
{chr(10).join(cards)}
    </div>"""


def gen_fun_ending(data: dict) -> str:
    fun = get(data, "narratives", "fun_ending", default={})
    if not fun:
        return ""
    return f"""
    <div class="fun-ending">
      <div class="fun-headline">"{e(fun.get("headline", ""))}"</div>
      <div class="fun-detail">{e(fun.get("detail", ""))}</div>
    </div>"""


def gen_feedback(data: dict) -> str:
    """Generate Team Feedback section."""
    feedback = get(data, "narratives", "feedback", default={})
    if not feedback:
        return ""
    team_items = feedback.get("team", [])
    model_items = feedback.get("model", [])
    if not team_items and not model_items:
        return ""
    cards = []
    if team_items:
        cards.append('      <div class="feedback-section"><h3>Team Observations</h3>')
        for item in team_items:
            title = e(item.get("title", ""))
            detail = e(item.get("detail", ""))
            evidence = e(item.get("evidence", ""))
            ev_html = f'\n          <div class="feedback-evidence">{evidence}</div>' if evidence else ''
            cards.append(
                f'        <div class="feedback-card team-card">\n'
                f'          <div class="feedback-title">{title}</div>\n'
                f'          <div class="feedback-detail">{detail}</div>{ev_html}\n'
                f'        </div>'
            )
        cards.append('      </div>')
    if model_items:
        cards.append('      <div class="feedback-section"><h3>Model Observations</h3>')
        for item in model_items:
            title = e(item.get("title", ""))
            detail = e(item.get("detail", ""))
            evidence = e(item.get("evidence", ""))
            ev_html = f'\n          <div class="feedback-evidence">{evidence}</div>' if evidence else ''
            cards.append(
                f'        <div class="feedback-card model-card">\n'
                f'          <div class="feedback-title">{title}</div>\n'
                f'          <div class="feedback-detail">{detail}</div>{ev_html}\n'
                f'        </div>'
            )
        cards.append('      </div>')
    intro = e(feedback.get("intro", ""))
    return f"""
    <h2 id="section-feedback" class="feedback-header">Team Feedback</h2>
    <p class="feedback-intro">{intro}</p>
{chr(10).join(cards)}"""


# ──────────────────────── Main generation ──────────────────────────────────
def generate_report(data: dict) -> str:
    """Generate the complete HTML report."""
    metrics = data.get("metrics", {})
    narratives = data.get("narratives", {})

    # Extract chart data
    tools = get(metrics, "tools", "tool_usage", default=[])
    languages = get(metrics, "tools", "languages", default=[])
    session_types = get(metrics, "messages", "session_types", default=[])

    what_wanted = get(narratives, "what_you_wanted", default=[])
    what_helped = get(narratives, "what_helped_most", default=[])
    outcomes = get(narratives, "outcomes", default=[])
    friction_types = get(narratives, "friction_types", default=[])
    satisfaction = get(narratives, "satisfaction", default=[])

    sections = [
        gen_header(data),
        gen_at_a_glance(data),
        gen_nav_toc(),
        gen_stats_row(data),
        gen_project_areas(data),
        gen_charts_row(
            "What You Wanted",
            what_wanted,
            "#2563eb",
            "Top Tools Used",
            tools,
            "#0891b2",
        ),
        gen_charts_row(
            "Languages", languages, "#10b981", "Session Types", session_types, "#8b5cf6"
        ),
        gen_usage_narrative(data),
        gen_response_time(data),
        gen_multi_clauding(data),
        gen_time_and_errors(data),
        gen_wins(data),
        gen_charts_row(
            "What Helped Most", what_helped, "#16a34a", "Outcomes", outcomes, "#8b5cf6"
        ),
        gen_friction(data),
        gen_charts_row(
            "Friction Types",
            friction_types,
            "#dc2626",
            "Inferred Satisfaction",
            satisfaction,
            "#eab308",
        ),
        gen_features(data),
        gen_patterns(data),
        gen_horizon(data),
        gen_feedback(data),
        gen_fun_ending(data),
    ]

    body = "\n".join(s for s in sections if s)

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>OpenCode Insights</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script>
    // Apply theme immediately to prevent flash
    (function() {{
      var s = localStorage.getItem('oci-theme');
      if (s === 'dark' || (!s && window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
        document.documentElement.setAttribute('data-theme', 'dark');
      }}
    }})();
    function toggleTheme() {{
      var current = document.documentElement.getAttribute('data-theme');
      var next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('oci-theme', next);
    }}
  </script>
  <style>{CSS}
  </style>
</head>
<body>
  <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle dark mode">
    <span class="icon-moon">\U0001f319</span>
    <span class="icon-sun">\u2600\ufe0f</span>
  </button>
  <div class="container">
{body}
  </div>
  <script>
{JS}
  </script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="OpenCode Insights Report Generator")
    parser.add_argument(
        "--input", "-i", required=True, help="Input JSON file (metrics + narratives)"
    )
    parser.add_argument("--output", "-o", required=True, help="Output HTML file")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    html_content = generate_report(data)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Report generated: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
