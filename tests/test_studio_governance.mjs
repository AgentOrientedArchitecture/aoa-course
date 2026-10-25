import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

// Exercise the real rendering path without starting SSE or making HTTP calls.
class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.textContent = ''; this.innerHTML = ''; }
  appendChild(child) { this.children.push(child); return child; }
}
function renderer(workflows = ['agent-card-check', 'cv-fit', 'flow-audit']) {
  const elements = new Map(['result-body', 'result-state'].map(id => [id, new Element('div')]));
  const context = vm.createContext({
    window: { STUDIO_CONFIG: { workflows }, addEventListener() {} },
    document: { createElement: tag => new Element(tag), getElementById: id => elements.get(id) },
    createStudioInspector: () => ({}),
  });
  const source = readFileSync(new URL('../system/services/studio/static/app.js', import.meta.url), 'utf8')
    .replace(/^import .*studio-inspector\.js.*;\n/, '');
  vm.runInContext(source + '\nglobalThis.renderTest = { state, renderResult, renderMarkdown };', context);
  return { ...context.renderTest, body: elements.get('result-body') };
}
const finding = severity => ({
  capability_id: 'evaluator-cv', article: 'Art 14', severity,
  checked: 'the recorded card declaration', evidence: { value: severity === 'green' ? 'Every verdict remains a draft.' : '' },
  gap: severity === 'red' ? 'Review declaration missing.' : '',
  regulation_citation: { passage_id: 'article14-p1', source_path: 'seed/article14.md', quote: 'Complete original passage.\nSecond line <script> is literal source text.' },
});
function setFindings(view, findings) {
  view.state.records = [{ step: 'response', capability: 'evaluator-agent-evidence', outputs: {
    findings, summary: { knowledge_evidence: { queries: { 'Art 14': 'article 14 human oversight' } } },
  } }];
}
const life = { workflow: 'agent-card-check', status: 'done', result: { findings_markdown: '# Full report\n\nOther AU findings remain here.' } };

test('card check focuses the recorded CV finding and preserves the complete estate report', () => {
  const view = renderer();
  setFindings(view, [{ ...finding('green'), capability_id: 'other-au' }, finding('red')]);
  view.renderResult(life);
  const [focus, full] = view.body.children;
  assert.equal(focus.tagName, 'section');
  assert.ok(focus.children.some(n => n.textContent === 'Recorded Article 14 finding: red.'));
  assert.ok(focus.children.some(n => n.textContent === 'Review declaration missing.'));
  assert.ok(focus.children.some(n => n.textContent === 'system/agents/evaluator/capabilities/cv/capability-card.yaml'));
  const quote = focus.children.find(n => n.textContent === finding('red').regulation_citation.quote);
  assert.equal(quote.tagName, 'blockquote');
  assert.equal(quote.innerHTML, ''); // Source content stays text, never executable markup.
  assert.equal(full.tagName, 'details');
  assert.equal(full.open, undefined); // The complete report starts collapsed.
  assert.equal(full.children[0].textContent, 'Full estate report');
  assert.deepEqual(full.children[1], view.renderMarkdown(life.result.findings_markdown));
});

test('green is shown only from the recorded finding; absent wiki evidence stays unknown', () => {
  for (const severity of ['green', 'unknown']) {
    const view = renderer();
    const item = finding(severity);
    if (severity === 'unknown') { item.regulation_citation = null; item.gap = 'No wiki passage.'; }
    setFindings(view, [item]);
    view.renderResult(life);
    const text = view.body.children[0].children.map(n => n.textContent).join('\n');
    assert.match(text, new RegExp(`Recorded Article 14 finding: ${severity}\\.`));
    if (severity === 'unknown') {
      assert.match(text, /No wiki passage/);
      assert.doesNotMatch(text, /The declaration is present/);
    }
  }
});

test('unrelated workflows and incomplete evidence retain the normal complete report', () => {
  const scenarios = [[], [finding('red')], [{ capability_id: 'evaluator-cv', article: 'Art 14' }]];
  for (const [index, findings] of scenarios.entries()) {
    const view = renderer();
    setFindings(view, findings);
    const current = index === 1 ? { ...life, workflow: 'flow-audit' } : life;
    view.renderResult(current);
    assert.equal(view.body.children.length, 1);
    assert.deepEqual(view.body.children[0], view.renderMarkdown(life.result.findings_markdown));
  }
});
