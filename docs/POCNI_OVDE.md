# Vaš lični QA agents repo

Ovo je alat koji držite odvojeno od projekata. Ne kopirate klijentov kod u ovaj repo.
Pokrećete ga nad lokalnom kopijom projekta i birate koje fajlove agent sme da vidi.

## Prvih pet minuta

Potrebni su Python 3.11 ili noviji i Git. Na Windowsu možete koristiti `py` umesto
`python` ako se tako pokreće Vaša Python instalacija. Otvorite terminal u folderu
`quality-agents` i pokrenite:

```sh
python -m quality_agents demo --out ../quality-demo
```

Otvorite ove fajlove u VS Code-u:

1. `../quality-demo/01-risk/report.md` — šta treba testirati i na kom nivou.
2. `../quality-demo/02-builder/result.json` — predloženi kod testa.
3. `../quality-demo/03-staged/changes.patch` — konkretna promena za review.
4. `../quality-demo/03-staged/verification.txt` — stvarno izvršavanje testova.
5. `../quality-demo/04-failure/report.md` — objašnjenje pronađenog buga.

Jedan test namerno pada: pravilo kaže da prijava u tačnom trenutku isteka roka mora
da bude odbijena, a kod je prihvata. To pokazuje da test proverava zahtev, a ne da
kopira postojeći bug. Demo odgovori agenata su unapred pripremljeni primeri, nisu
AI analiza. Za pravu analizu koristite jedan od naredna dva načina.

## Način A: uz coding assistant koji već koristite

1. Napravite konfiguraciju: `python -m quality_agents init --out ../projekat.qa.json`.
2. Upišite opis projekta, bitne putanje i dozvoljene test foldere.
3. Pripremite packet komandom `prepare risk` iz README-a.
4. Pregledajte `prompt.md` da znate šta delite sa asistentom.
5. Dajte taj fajl asistentu i sačuvajte njegov JSON odgovor u `response.json`.
6. Komanda `import` proverava strukturu, navedene fajlove i linije.
7. Vi proveravate smisao scenarija; `approve` beleži Vašu odluku.
8. Isto ponovite za `prepare builder`, pa pregledajte i odobrite predloženi kod.
9. `stage` napravi kopiju projekta sa testovima; `verify` izvršava komandu koju Vi navedete.
10. Ako test padne, `prepare failure --evidence ...` priprema podatke za trećeg agenta.

Ovaj način koristi ručnu razmenu fajlova. Nema automatskog povezivanja na Vašu
ChatGPT pretplatu. Rad sa istim agentom u tri razgovora je dovoljan: razlikuju se
ulazni podaci, instrukcije, schema izlaza i odgovornost.

## Način B: automatski preko API-ja

Nakon `prepare`, umesto ručnog slanja koristite:

```sh
python -m quality_agents run --run ../qa-runs/story-42-risk --model YOUR_MODEL_ID --send
```

Potrebno je lokalno podesiti `OPENAI_API_KEY`. Ne upisujte ključ u repo ili chat.
Model birate prema pristupu koji imate na nalogu; nema hardkodovanog modela.
`--send` je svesna odluka da odabrani kontekst ide API provajderu. Pregledajte
`prompt.md` pre toga. API poziv se posebno naplaćuje po pravilima provajdera.

## Kako pokrenuti proveru na Windowsu bez problema sa JSON navodnicima

Iz Python terminala, ili iz svog kratkog lokalnog Python skripta:

```python
from quality_agents.workflow import verify

result = verify(
    r"C:\work\qa-runs\story-42-stage",
    [r"C:\work\test-env\Scripts\python.exe", "-m", "pytest", "tests", "-q"],
)
print(result)
```

Biblioteke koje testovi koriste moraju postojati u tom okruženju. `stage` namerno
ne kopira `.venv`, `node_modules`, kredencijale ili Git hookove. Kod za testiranje
ima ista OS prava kao proces koji ga pokreće: kopija projekta nije sandbox.

## Kako ovo smanjuje QA bottleneck

QA manje vremena troši na sastavljanje prvog nacrta scenarija, ponavljanje UI
provera i skupljanje logova. Developer dobija konkretan predlog testova i dokaz
zašto nešto pada. QA i dalje radi procenu rizika, exploratory i cross-system rad.

Ne uvodite obavezni QA potpis na svaku sitnu izmenu: time biste napravili novi red
čekanja. Za mali rizik developer može biti reviewer; QA uključujete u rizične
promene i uzorkovanje. Sama skripta ne rešava nejasne zahteve, loše okruženje ili
nedostatak vremena u sprintu. Merite ukupno ljudsko vreme, uključujući review.

## Šta je zaista provereno

Pogledajte `docs/VALIDATION.md`. Offline tok i testovi orkestracije su izvršeni.
Poziv pravom modelu zahteva Vaš ključ i pristup; nije predstavljen kao izvršen ako
nije. Windows CI je pripremljen, a njegov status treba potvrditi nakon GitHub objave.
