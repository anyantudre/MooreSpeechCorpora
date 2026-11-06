---
license: cc-by-nc-4.0
language:
- '{{iso}}'
pipeline_tag: '{{automatic-speech-recognition or text-to-speech}}'
base_model: '{{owner/base-model}}'
datasets:
- '{{owner/training-dataset}}'
tags:
- '{{language name, lowercase}}'
- '{{method, e.g. ctc}}'
extra_gated_heading: 'Request access to {{model-name}}'
extra_gated_prompt: '{{model-name}} is shared for non-commercial research (CC BY-NC 4.0). Requests are reviewed by hand, usually within a few days. Commercial use needs written permission from nyantudrealban@gmail.com.'
extra_gated_fields:
  First name(s): text
  Last name: text
  Email address where we can reach you (work or academic if possible): text
  Affiliation (university, institution or company): text
  Country: country
  Role:
    type: select
    options: [Student, Researcher or academic staff, Engineer or developer, Journalist or media, Independent, Other]
  Intended use:
    type: select
    options: [Academic research, Teaching, Non-profit or community project, Commercial product or service, Industrial R&D, Personal project, Other]
  Describe your project and how you will use the model (2-3 sentences): text
  Will you use the model commercially?:
    type: select
    options: ['Yes', 'No', Not sure]
  Do you speak {{Language}}?:
    type: select
    options: [Native speaker, Second language, 'No']
  May we contact you about evaluations or collaborations on {{Language}} language technology?:
    type: select
    options: ['Yes', 'No']
  I will use this model for non-commercial purposes only, unless written permission is given: checkbox
  I will use this model for research and evaluation only: checkbox
  I will cite this model if I use it in a publication: checkbox
extra_gated_button_content: Submit request
---

<!--
Model card template for the personal models on Hugging Face (anyantudre). Reference cards:
anyantudre/mos-w2v-bert-2.0-bench and anyantudre/mos-w2v-bert-2.0-jw. Copy this file to README.md in the
model repo, fill every {{placeholder}} and delete this comment. The YAML block stays at the top.

Name
- {lang}-{base}-{size}[-{direction}][-{data}][-lora][-YYYYMM], lowercase, on anyantudre.
  Examples: mos-w2v-bert-2.0-bench, mos-w2v-bert-2.0-jw.

License and access
- CC BY-NC 4.0 with a manual gate: the form above, including "research and evaluation only".
- Commercial use contact: nyantudrealban@gmail.com, in the gate prompt and in the License section.
- Citation author: Wendyellé Abubakrh Alban Nyantudre only.
- No "Developed and maintained by" section. Tags describe the language and the method only.

Layout
- Order: title, tagline, badges, opening paragraph, "Résumé en français", then the sections below.
- Badges on one line, brown (#4A2E17 / #B0723A), each <img> with style="display: inline-block;
  vertical-align: middle;".
- The Résumé is a full French version of the tagline and opening paragraph (what the model is, what it
  was trained on, access and license), so a French-only reader gets everything. No "En bref".
- Sections: what it is (table), quick start, training data (exact sources and hours, held-out rule),
  evaluation (benchmark, version, normaliser, scores with confidence intervals, or "pending"), limits,
  license, citation.

Style (same as the dataset cards)
- Professional and short. Run the text through the humanizer skill before publishing.
- No em dashes, no emojis in headings, no AI wording.
- Every number comes from the training logs or the evaluation; say what is pending or weak.
-->

<h1 align="center">{{model-name}}</h1>

<p align="center">
  {{One-line tagline: task, language, base model.}}<br>
  <img alt="Language: {{Language}}" src="https://img.shields.io/badge/language-{{Language}}%20({{iso}})-4A2E17" style="display: inline-block; vertical-align: middle;"> <img alt="Task: {{task}}" src="https://img.shields.io/badge/task-{{task}}-B0723A" style="display: inline-block; vertical-align: middle;"> <img alt="License: CC BY-NC 4.0" src="https://img.shields.io/badge/license-CC%20BY--NC%204.0-4A2E17" style="display: inline-block; vertical-align: middle;">
</p>

{{model-name}} is a {{Language}} {{speech recognition / text-to-speech}} model, fine-tuned from {{base model}}. {{What it is for, in one or two sentences, and what makes it different from related models.}}

> **Résumé en français.** {{A full French version of the tagline and the paragraph above: task, base model, training data, access on request for non-commercial research, commercial use on written permission.}}

| | |
|---|---|
| Task | {{Task, language, sample rate}} |
| Base model | [{{owner/base-model}}](https://huggingface.co/{{owner/base-model}}) |
| Training data | [{{owner/dataset}}](https://huggingface.co/datasets/{{owner/dataset}}) at revision `{{commit}}`, {{split and sources}} |
| Trained | {{Month YYYY}} |
| Related | {{Related models, with links}} |

## Quick start

```python
{{Minimal loading and inference code.}}
```

## Training

- {{Clips and hours per source, exactly as used.}}
- {{Held-out rule: which evaluation chapters, speakers or sentences were removed from every source.}}
- {{Epochs, steps, batch, learning rate, which checkpoint is kept and why.}}
- {{Terms of the training audio, and that the weights contain no audio or text.}}

## Evaluation

| Set | {{Metric}} | {{Metric}} |
|---|---|---|
| {{Benchmark and version, split, size}} | {{score with 95% CI}} | {{score with 95% CI}} |

{{Normaliser and version, decoding settings. Scores not yet measured: "pending".}}

## Limits

- {{Domain, speakers seen in training, known failure cases.}}

## License

CC BY-NC 4.0. Commercial use needs written permission from nyantudrealban@gmail.com.

## Citation

```bibtex
@misc{nyantudre{{year}}{{key}},
  title        = {{{model-name}}: {{subtitle}}},
  author       = {Nyantudre, Wendyellé Abubakrh Alban},
  year         = {{{year}}},
  howpublished = {Hugging Face Models},
  url          = {https://huggingface.co/anyantudre/{{model-name}}}
}
```
