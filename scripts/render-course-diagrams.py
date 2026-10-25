#!/usr/bin/env python3
"""Regenerate the course's editable SVG architecture diagrams (stdlib only)."""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'course/diagrams'
COLOURS = {'control': ('#eaf1fb', '#32649a'), 'au': ('#e7f4ee', '#23775b'),
           'model': ('#fff3dc', '#94621c'), 'store': ('#f0ecfa', '#715391'),
           'stop': ('#fbeeed', '#a94d44'), 'plain': ('#ffffff', '#5b6c78')}


class Diagram:
    def __init__(self, name, title, subtitle, height=780):
        self.name = name
        self.parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#516775"/></marker></defs>
<style>text{{font-family:Arial,Helvetica,sans-serif;fill:#203847}}.title{{font-size:30px;font-weight:700}}.sub{{font-size:18px;fill:#536875}}.head{{font-size:23px;font-weight:700}}.body{{font-size:18px}}.label{{font-size:16px;fill:#405866;paint-order:stroke;stroke:#fafbf9;stroke-width:7px;stroke-linejoin:round}}</style>
<rect width="1200" height="{height}" fill="#fafbf9"/>
<text x="40" y="48" class="title">{escape(title)}</text>
<text x="40" y="82" class="sub">{escape(subtitle)}</text>''']

    def text(self, x, y, text, cls='body', anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(text)}</text>')

    def box(self, x, y, w, h, title, lines, kind='control'):
        bg, stroke = COLOURS[kind]
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{bg}" stroke="{stroke}" stroke-width="1.5"/>')
        self.parts.append(f'<rect x="{x}" y="{y+15}" width="5" height="{h-30}" rx="2" fill="{stroke}"/>')
        self.text(x+20, y+35, title, 'head')
        for i, line in enumerate(lines):
            self.text(x+20, y+65+26*i, line)

    def arrow(self, d, label=None, at=None, dashed=False):
        dash = ' stroke-dasharray="7 5"' if dashed else ''
        self.parts.append(f'<path d="{d}" fill="none" stroke="#516775" stroke-width="2"{dash} marker-end="url(#arrow)"/>')
        if label:
            self.text(*at, label, 'label', 'middle')

    def save(self):
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f'{self.name}.svg').write_text('\n'.join(self.parts) + '\n</svg>\n')


d = Diagram('components', 'The course system', 'One browser, a small control plane, and independently running capabilities.', 800)
d.box(450, 120, 300, 100, 'Studio · 8080', ['Submit work; inspect evidence', 'Review the held result'], 'plain')
d.box(40, 290, 300, 145, 'Registry · 7100', ['Capability contracts and IDs', 'Lifecycle metadata', 'Cards persist in cards.json'])
d.box(450, 270, 300, 180, 'Planner service · 7200', ['Propose and validate a plan', 'Select and invoke AUs', 'Manage result review', 'These roles share a process'])
d.box(860, 290, 300, 145, 'Decision API · 7250', ['A bounded named choice', 'TypeSafe or local Ollama', 'No authority to invoke an AU'], 'model')
d.box(450, 540, 300, 135, 'Agentic Units', ['Python runtimes or EVE', 'Each fulfils its public contract', 'Models and tools live inside'], 'au')
d.box(40, 540, 300, 135, 'Tool bridges', ['Document text, files, wiki', 'Registered as kind: tool', 'HTTP bridge → MCP server'], 'au')
d.box(860, 540, 300, 135, 'Case store', ['SQLite snapshots and events', 'JSONL audit projection', 'Revised profile'], 'store')
d.arrow('M600 220V270', 'intent / review', (680, 249))
d.arrow('M450 335H340', 'read cards', (395, 322))
d.arrow('M750 335H860', 'ask for choice', (805, 322))
d.arrow('M600 450V540', 'A2A invocation', (686, 500))
d.arrow('M450 600H340', 'tool call', (395, 587))
d.arrow('M750 410H800V600H860', 'persist', (819, 500))
d.text(40, 725, 'AUs and tools publish cards to the registry at boot. Studio receives registry and trace events.', 'sub')
d.text(40, 755, 'Generation calls use Cerebras or Ollama. External Directory discovery is shown in the Session 3 diagram.', 'sub')
d.save()

d = Diagram('cv-selection', 'From an intent to an executable plan', 'Session 1 · separate a proposed task, a model choice and an accepted binding.', 820)
d.box(40, 140, 330, 155, '1  Propose tasks', ['CV + job + assessment emphasis', 'LLM proposal or recorded fallback', 'Required course tasks stay fixed'])
d.box(435, 140, 330, 155, '2  Filter contracts', ['Approved AU lifecycle', 'Compatible inputs and outputs', 'Code checks eligibility'])
d.box(830, 140, 330, 155, '3  Choose a fit', ['Decision model if several eligible', 'One eligible: bind without a model', 'No fit / low probability: stop'], 'model')
d.box(435, 405, 330, 130, '4  Validate composition', ['All required responsibilities', 'Correct evidence dependencies', 'Only then accept the bindings'])
d.box(40, 405, 330, 130, 'Stop before execution', ['Invalid composition or no choice', 'Inspect the reason and clarify'], 'stop')
d.box(830, 405, 330, 130, 'CV evaluator candidates', ['General · data · frontend', 'Separate runtimes and Agent IDs', 'Same input/output contract'], 'plain')
d.box(40, 650, 300, 110, 'Parse CV', ['parser-cv', 'Structured CV evidence'], 'au')
d.box(450, 650, 300, 110, 'Assess fit', ['The selected evaluator', 'Scores, gaps and rationale'], 'au')
d.box(860, 650, 300, 110, 'Report', ['reporter-cv-fit', 'The returned assessment'], 'au')
d.arrow('M370 215H435'); d.arrow('M765 215H830')
d.arrow('M995 295V350H600V405', 'proposed bindings', (770, 340))
d.arrow('M435 470H370', 'invalid', (400, 457))
d.arrow('M600 535V595H190V650', 'valid plan → run the application AUs', (400, 582))
d.arrow('M340 705H450'); d.arrow('M750 705H860')
d.text(40, 795, 'A valid contract and a high model probability do not establish assessment quality.', 'sub')
d.save()

d = Diagram('wiki-decision', 'A decision model inside an AU', 'Session 2 · the judgement changes; the parser, reporter and wiki contracts remain usable.', 670)
d.box(40, 145, 300, 155, 'Parse the note', ['parser-notes', 'Generation model extracts fields', 'Inspect the extracted passages'], 'au')
d.box(450, 145, 300, 155, 'Assess promotion', ['evaluator-promote', 'Code gates the returned choice', 'Retains the parsed quotes'], 'au')
d.box(860, 145, 300, 155, 'Report / publish', ['reporter-ingest-summary', 'Writes only if promote is true', 'Reject / review: withhold'], 'au')
d.box(450, 405, 300, 140, 'Decision API', ['promote · reject · review', 'Choice + available probability', 'Provider, model and latency'], 'model')
d.box(860, 405, 300, 140, 'Wiki store', ['Registered tool and MCP server', 'Promoted evidence and index', 'Supports later grounded queries'], 'store')
d.arrow('M340 220H450', 'parsed evidence', (395, 205)); d.arrow('M750 220H860', 'promotion', (805, 205))
d.arrow('M560 300V405', 'request', (510, 355)); d.arrow('M640 405V300', 'choice', (685, 355))
d.arrow('M1010 300V405', 'promote only', (1080, 355))
d.text(40, 595, 'AU code sends uncertain choices and promotions with no usable passages to review.', 'sub')
d.text(40, 630, 'Review is recorded and withheld. There is no separate human promotion queue.', 'sub')
d.save()

d = Diagram('eve-adoption', 'Build, discover and adopt', 'Session 3 · EVE runs the agent; Directory stores its description; AOA composes the capability.', 800)
d.box(40, 145, 300, 150, 'Native EVE', ['Author and test the interviewer', 'agent.ts + instructions.md', 'No AOA registration yet'], 'au')
d.box(450, 145, 300, 150, 'Course adoption bridge', ['Reuse the authored files', 'Add card, Agent ID and trace', 'Expose the A2A boundary'])
d.box(860, 145, 300, 150, 'Local AOA registry', ['Live capability and endpoint', 'Contract + lifecycle metadata', 'Used by this course planner'])
d.box(40, 470, 300, 155, 'AGNTCY Directory', ['Real local dirctl daemon', 'OASF record: publish / find / pull', 'Metadata; does not run EVE'], 'store')
d.box(450, 470, 300, 155, 'Compare the record', ['Course check compares hashes', 'And local lifecycle status', 'Does not import or invoke'])
d.box(860, 470, 300, 155, 'Compose and execute', ['Select local capabilities', 'Validate the complete plan', 'Invoke the adopted interviewer'], 'au')
d.arrow('M340 220H450', 'adopt', (395, 205)); d.arrow('M750 220H860', 'register', (805, 205))
d.arrow('M190 295V470', 'export contract template', (190, 390), dashed=True)
d.arrow('M340 545H450', 'pulled record', (395, 530), dashed=True)
d.arrow('M960 295V365H600V470', 'local contract', (760, 353), dashed=True)
d.arrow('M1090 295V470', 'runtime discovery', (1090, 405))
d.text(40, 680, 'Dashed arrows carry descriptions. Publication in Directory never grants local execution permission.', 'sub')
d.text(40, 715, 'The exported card can be the unadopted template or the registered card. Both paths are in the lab.', 'sub')
d.text(40, 750, 'The same learner-authored EVE agent runs before and after adoption.', 'sub')
d.save()

d = Diagram('eve-invocation', 'One call across the EVE boundary', 'The planner speaks the AU contract. The bridge translates it into a real EVE session.', 610)
d.box(40, 145, 300, 165, 'AOA planner service', ['After CV parsing and evaluation', 'Inputs: evaluation + optional CV', 'Selected interviewer contract'])
d.box(450, 145, 300, 165, 'Course bridge · 7311', ['A2A message/send → inputs', 'Contract-derived JSON prompt', 'Parse reply; report signals'])
d.box(860, 145, 300, 165, 'EVE runtime', ['eve dev --no-ui', 'eve/client creates a session', 'Learner agent calls its model'], 'au')
d.box(450, 435, 300, 110, 'AOA result envelope', ['questions + report_markdown', 'Presence checks and latency'], 'plain')
d.arrow('M340 225H450', 'A2A v0.3 shape', (395, 210))
d.arrow('M750 225H860', 'EVE client', (805, 210))
d.arrow('M1010 310V365H700V310', 'final assistant text', (855, 353))
d.arrow('M600 310V435', 'parsed JSON', (600, 395))
d.arrow('M450 490H190V310', 'result + trace ID', (190, 395))
d.text(40, 585, 'Generic signals check shape and field presence. Native acceptance still checks question quality and limits.', 'sub')
d.save()

d = Diagram('durable-case', 'The result belongs to a continuing case', 'Session 4 · persist the exact draft and the decision made about it.', 850)
d.box(40, 140, 300, 125, 'Check eligibility', ['Selected cards + release policy', 'Wiki supplies cited rationale'])
d.box(450, 140, 300, 125, 'Run the application AUs', ['Read / compute / draft', 'No employment action'], 'au')
d.box(860, 140, 300, 125, 'Hold the draft', ['Freeze the result and digest', 'Save with the case and events'], 'store')
d.box(40, 365, 300, 100, 'Rejected', ['No application invocation'], 'stop')
d.box(450, 365, 300, 100, 'Interrupted', ['Inspect; no automatic rerun'], 'stop')
d.box(860, 365, 300, 100, 'Human review', ['Exact digest + reviewer notes'])
d.box(665, 575, 235, 100, 'Released', ['Identical reviewed draft'], 'au')
d.box(925, 575, 235, 100, 'Quarantined', ['Result withheld'], 'stop')
d.arrow('M340 200H450', 'proceed', (395, 186)); d.arrow('M750 200H860', 'completed', (805, 186))
d.arrow('M190 265V365', 'ineligible', (190, 320))
d.arrow('M600 265V365', 'restart during execution', (600, 320))
d.arrow('M1010 265V365', 'reopen saved case', (1010, 320))
d.arrow('M960 465V520H782V575', 'approve', (850, 507))
d.arrow('M1060 465V575', 'reject', (1100, 525))
d.box(40, 725, 1120, 90, 'SQLite is authoritative; JSONL is an audit projection', ['A held draft survives restart. Identical review retries add no second release. External effects are not replayed.'], 'store')
d.save()
