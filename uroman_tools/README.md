# Uroman Tools
Minimal Universal Romanizer tools extracted from the uroman project.

## Source
Extracted from: https://github.com/isi-nlp/uroman
- **License**: Apache 2.0
- **Original Authors**: Ulf Hermjakob (USC/ISI)

## Components
- `bin/uroman.pl`: main romanization script
- `lib/`: essential Perl modules
- `data/`: romanization tables and Unicode data

## Usage
```bash
# Direct usage
echo "текст" | perl uroman_tools/bin/uroman.pl

# With language code
echo "مرحبا" | perl uroman_tools/bin/uroman.pl -l ara
```

## Dependencies
- Perl with standard modules 