---
pretty_name: "{{DatasetName}}"
language:
- "{{iso}}"                    # ISO 639-3, e.g. mos, dyu. Add fr only when a subset has French text or audio.
license: other                 # we do not own the audio: never put cc-by-* here for third-party recordings
license_name: third-party-audio-cc-by-nc-annotations   # lowercase slug only (Hub rule)
license_link: https://huggingface.co/datasets/{{owner}}/{{DatasetName}}#license
license_details: Audio and source texts belong to their owners (no license granted). Our annotations are CC BY-NC 4.0.
task_categories:
- automatic-speech-recognition
- text-to-speech
size_categories:
- "1K<n<10K"                    # n<1K, 1K<n<10K, 10K<n<100K...
tags:
- speech
- audio
- "{{language}}"
- burkina-faso
- low-resource
- fasospeechcorpora
configs:
- config_name: default          # everything; loads when no subset is named
  data_files:
  - split: train
    path:                       # list the subset folders instead of storing the clips twice
    - "{{subset}}/train-*"
- config_name: "{{subset}}"     # one per category or source
  data_files:
  - split: train
    path: "{{subset}}/train-*"
# Gate: the same form on every gated dataset. Only the heading and the prompt change.
extra_gated_heading: "Request access to {{DatasetName}}"
extra_gated_prompt: '{{DatasetName}} collects publicly available {{Language}} speech, aligned with its text, for
  speech recognition and text-to-speech research. This version holds {{content}}. Requests are reviewed by hand,
  usually within a few days. The recordings come from {{third-party publications, owners named}}. They are shared
  for non-commercial research only and remain the property of their owners. License: CC BY-NC 4.0 for our
  annotations only; the audio and texts stay the property of their owners.'
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
  Describe your project and how you will use the dataset (2-3 sentences): text
  Will you use the dataset or the audio it contains commercially?:
    type: select
    options: ['Yes', 'No', Not sure]
  Do you agree to comply with the license stated above?:
    type: select
    options: ['Yes', 'No', Not sure]
  "Do you speak {{Language}}?":
    type: select
    options: [Native speaker, Second language, 'No']
  "May we contact you about listening tests or collaborations on {{Language}} speech technology?":
    type: select
    options: ['Yes', 'No']
  I will not redistribute the audio or the transcripts, in whole or in part: checkbox
  I understand the recordings come from third-party publications, are provided for non-commercial research only, and remain the property of their owners: checkbox
  I will cite this work if I use it in a publication: checkbox
extra_gated_button_content: Submit request
---

<!--
Dataset card template for the FasoSpeechCorpora datasets on Hugging Face (anyantudre and goaicorp).
Copy this file to README.md in the dataset repo, fill every {{placeholder}}, delete sections that stay empty
and delete this comment. The YAML block must stay at the very top of the file.

Framing
- A {Language}SpeechCorpora dataset aims to collect all publicly available speech in that language with its
  text. Say what this version holds and that later versions add sources. Never describe the corpus by its
  current content alone.

Rights
- Credit every owner by name (author, reader, publisher) in Sources and credits, with what their terms say.
- Never claim a license on audio we do not own. CC BY-NC 4.0 covers only our annotations.
- Sources with different owners or terms go in separate subsets, each with its own credit line.
- Material whose terms forbid posting it online (jw.org, for example) never goes in a public dataset.

Images
- Load the logo from the public GitHub repo (as below), never from the dataset repo: files in a gated repo
  return 401 to visitors without access, so the logo would be broken on the access-request page.

Columns
- `category` for the content type (conte, devinette, proverbe, bible...), never `genre` (in French it also
  means male or female). `voice` is the reader's voice, `male` or `female`.
- Subset names are lowercase (contes, devinettes, proverbes, bible, asr).

Style (same as the GitHub READMEs)
- Professional and short. Run the text through the humanizer skill before publishing.
- No em dashes, no emojis in headings, no AI wording.
- Numbers come from the data (clips, hours, CER). Say what is missing or weak.
- Before uploading, validate the YAML: DatasetCard.load("README.md").validate("dataset").
- Tag the current version (create_tag) before replacing its data, so old code can use `revision=`.
-->

<p align="center">
  <img alt="FasoSpeechCorpora" src="https://raw.githubusercontent.com/anyantudre/FasoSpeechCorpora/main/assets/brand/png/fasospeechcorpora-horizontal.png" width="420">
</p>

<h1 align="center">{{DatasetName}}</h1>

<p align="center">
  Publicly available {{Language}} speech, aligned with its text, for speech recognition and text-to-speech.<br>
  <img alt="Language: {{Language}}" src="https://img.shields.io/badge/language-{{Language}}%20({{iso}})-4A2E17">
  <img alt="{{hours}} hours" src="https://img.shields.io/badge/audio-{{hours}}%20h-B0723A">
  <img alt="License: see card" src="https://img.shields.io/badge/license-see%20card-4A2E17">
  <a href="https://github.com/anyantudre/FasoSpeechCorpora"><img alt="Built with FasoSpeechCorpora" src="https://img.shields.io/badge/built%20with-FasoSpeechCorpora-B0723A"></a>
</p>

> **En bref.** {{Two or three sentences in French: what it is, what this version holds, how many hours, access on request for non-commercial research.}}

{{DatasetName}} aims to collect all publicly available {{Language}} (ISO 639-3 `{{iso}}`) speech, cut into sentences and paired with its text, for speech recognition and text-to-speech research. This version holds {{content}}. Next versions add more sources.

The same work extends to other languages of Burkina Faso through [FasoSpeechCorpora](https://github.com/anyantudre/FasoSpeechCorpora), the toolkit that builds these corpora.

> [!NOTE]
> Access is gated and requests are reviewed by hand. Anonymous or vague requests will not be approved.

## Overview

- {{N}} clips, {{H}} hours, 16 kHz mono
- {{n}} speakers: {{who}}
- {{One quality figure, e.g. median CER 0.050}}

| Subset | Content | Clips | Hours | Speakers |
|---|---|---|---|---|
| `default` | All subsets below | | | |
| `{{subset}}` | {{content}} | | | |

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("{{owner}}/{{DatasetName}}", split="train")                    # default
part = load_dataset("{{owner}}/{{DatasetName}}", "{{subset}}", split="train")    # one subset
```

Log in first (`hf auth login`) with an account that has been granted access.

## Columns

| Column | Type | Description |
|---|---|---|
| `audio` | Audio (16 kHz) | The clip |
| `text` | string | {{Language}} transcript |
| `duration` | float | Length in seconds |
| `voice` | string | Reader's voice: `male` or `female` |
| `speaker_id` | int | Speaker label |
| `category` | string | {{Content type, e.g. conte, devinette, proverbe}} |
| {{...}} | | |

## Sources and credits

| Source | Authors and readers | Owner and terms | Clips | Hours |
|---|---|---|---|---|
| {{Book or recording, with link}} | {{Who wrote and who reads it}} | {{Owner; what their terms say, with link}} | | |

{{Thank the publishers, authors and readers, and name the tools: MMS, uroman, Demucs, the ASR models used.}}

## How it was built

Built with [FasoSpeechCorpora](https://github.com/anyantudre/FasoSpeechCorpora), recipes in [`{{recipes/...}}`](https://github.com/anyantudre/FasoSpeechCorpora/tree/main/{{recipes/...}}).

1. **Fetch and prepare:** {{download, 16 kHz mono, text clean-up}}
2. **Align:** {{forced alignment method}}
3. **Trim, verify, filter:** {{with the thresholds}}

## Limits

- {{Speakers, content type, known transcript errors, what was dropped and why.}}

## Access

Fill in the form on this page. Requests are approved for people and institutions that say who they are, describe a research or academic use, and accept the non-commercial terms. Questions: Wendyellé A. Alban NYANTUDRE ([nyantudre@gmail.com](mailto:nyantudre@gmail.com)).

## License

- **Audio and source texts:** property of the owners listed in Sources and credits. No license is granted on them; they are shared for non-commercial research and their owners can ask for removal.
- **Our work** (segmentation, alignment, corrected transcripts, metadata): CC BY-NC 4.0.

For other uses, contact us. By accessing this dataset you agree to these terms.

## Citation

```bibtex
@misc{nyantudre{{year}}{{key}},
  title        = {{{DatasetName}}: {{subtitle}}},
  author       = {Nyantudre, Wendyellé Abubakrh Alban and Bandaogo, Aristide},
  year         = {{{year}}},
  howpublished = {Hugging Face Datasets (gated access)},
  url          = {https://huggingface.co/datasets/{{owner}}/{{DatasetName}}}
}
```

## Contacts

- Wendyellé A. Alban NYANTUDRE, curator: [nyantudre@gmail.com](mailto:nyantudre@gmail.com), [LinkedIn](https://www.linkedin.com/in/anyantudre)
- Aristide BANDAOGO: [aristide@goaicorporation.org](mailto:aristide@goaicorporation.org)
