# Kako da koristiš tri agenta

Radiš u projektu koji želiš da testiraš, u Cursor-u, Claude Code-u ili Codex-u. Ne moraš da
kloniraš quality-agents niti da pokrećeš Python komande. Coding asistent je koordinator;
tri odvojena subagenta rade analizu, testove i nezavisan review.

## Jednom: instalacija

Otvori terminal u svom projektu i pokreni:

```sh
npx skills@latest add milosmilicevicsf/quality-agents
```

Izaberi oba skilla i asistenta koji koristiš. To je isti postupak kao za sdet-skills.
Za sve buduće projekte možeš izabrati globalnu instalaciju. Potrebni su Node i Git,
kao i coding asistent koji podržava subagente. Zaseban API ključ nije potreban.

## Jednom po projektu: setup tima

U Cursor Agent ili Claude Code chat upiši `/setup-quality-agents`.
U Codex-u upiši `$setup-quality-agents` ili izaberi skill iz liste.

Asistent sam registruje Risk Analyst, Test Engineer i Quality Reviewer, pročita
postojeći test framework i sačuva konfiguraciju. Ako već imaš sdet-skills setup,
koristi njegov `docs/agents/testing.md`. Nema ponovnog popunjavanja istih stvari.
Ako novi agenti nisu vidljivi, zatvori i ponovo otvori coding asistenta.

## Svaki zadatak: jedna poruka

Za analizu, u Cursor Agent ili Claude Code chatu:

```text
/quality-flow Analiziraj ovaj story i predloži testove: [nalepi story i acceptance criteria]
```

Za stvarno pisanje i pokretanje testova:

```text
/quality-flow Analiziraj ovaj story, napiši i pokreni regresione testove,
pa neka Quality Reviewer nezavisno pregleda rezultat: [story]
```

U Codex-u koristi `$quality-flow` umesto `/quality-flow`. Možeš i običnom porukom
tražiti da koristi quality-flow tim. Ovo se piše u chat asistenta, ne u terminal.

Za instalaciju samo u Cursor možeš koristiti
`npx skills@latest add milosmilicevicsf/quality-agents --agent cursor`.
Setup pravi tri fajla u `.cursor/agents/`. Ako si instalirao raniju verziju, ponovi
instalaciju, pokreni setup i otvori novi Agent razgovor ako agenti nisu vidljivi.

## Šta ćeš videti

1. Risk Analyst čita zahtev i kod i pravi plan sa scenarijima i nivoima testiranja.
2. Drugi agent, Test Engineer, preuzima plan i piše testove ako si to tražio.
3. Treći agent, Quality Reviewer, dobija originalni zahtev, kod, diff i logove.
   Sam proverava šta ne valja; ne dobija zadatak da potvrdi zaključak autora testova.
4. Koordinator ti daje jedan HTML izveštaj i kratak zaključak u chatu.

U izveštaju vidiš identitete pokrenutih agenata, šta je pregledano, šta je promenjeno,
koji testovi jesu ili nisu pokrenuti, gde postoje rupe i šta je sledeći korak.
HTML se otvara direktno, radi bez interneta i možeš ga poslati drugome.
Lokalni izveštaji su u privremenom folderu van projekta; kopiraj važan izveštaj u
trajni folder. U hostovanom okruženju koristi link ka sačuvanom fajlu.

Nijedan agent ne odobrava release umesto tebe. Jedan smislen test koji otkrije bug
ostaje crven; agent ne menja očekivani rezultat da bi test prošao.

## Ako nešto ne radi

- **Komanda nije prepoznata u terminalu:** `/quality-flow` ide u chat asistenta.
- **Skill nije vidljiv:** proveri da si instalirao oba skilla za pravi asistent i
  pokreni novi razgovor/session.
- **Agent nije vidljiv:** ponovo otvori asistent nakon setup-a. Stariji Codex može
  zahtevati ažuriranje da učita samostalne definicije u `.codex/agents/`.
- **Nema podrške za subagente:** setup to mora jasno da kaže. Tri odvojena agenta
  ne mogu nastati samo promenom prompta u jednom razgovoru.
- **Testovi nisu pokrenuti:** izveštaj navodi razlog, npr. nedostupno test okruženje.
- **Već prilagođen agent:** setup ga ne prepisuje; pregledaj razliku s asistentom.

Python kod u repou je dodatna opcija za API/CI automatizaciju. Za ovaj način rada
ne koristiš prepare/import/approve komande i ne prebacuješ JSON ručno.
