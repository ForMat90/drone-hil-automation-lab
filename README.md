# Drone HIL Automation Lab

**Test automatici end-to-end su un drone simulato in Gazebo, pilotato via ROS 2 e verificato con Playwright.**

[![tests](https://github.com/ForMat90/drone-hil-automation-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/ForMat90/drone-hil-automation-lab/actions/workflows/tests.yml)

[English version](README.en.md) · [Provarlo con Docker](#provarlo-con-docker) · [Come avviare](#cosa-serve-installato) · [Come comunicano i pezzi](#come-parlano-tra-loro-i-pezzi)

![Demo: il drone eseguito dai test automatici in Gazebo](docs/demo.gif)

*Nessuno sta toccando la tastiera: è `npx playwright test` che muove il drone. Video a velocità reale: [docs/demo.mp4](docs/demo.mp4).*

Lancio `npx playwright test` e il drone si muove da solo nella scena 3D: va a sinistra, a destra, avanti, indietro, sale, scende e ruota. A ogni manovra un assert verifica che abbia fatto davvero quello che il comando prometteva.

### Il problema interessante

Gazebo e ROS 2 girano dentro Linux (WSL) e comunicano con messaggi ROS. Playwright gira su Windows e parla HTTP. Sono due mondi che non possono chiamarsi direttamente, quindi ho scritto un **servizio ponte** che espone quattro API e le traduce in comandi ROS — lo stesso approccio che si usa per far dialogare microservizi scritti in linguaggi diversi.

```
npx playwright test  ──HTTP──▶  ponte Python (:8765)  ──ROS 2──▶  Gazebo
   (Windows, JS)                    (Linux/WSL)                   (drone 3D)
```

### Cosa dimostra il progetto

- **Piramide dei test completa**: unit test veloci sulla logica di volo, test end-to-end sul sistema reale in esecuzione.
- **Assert su un sistema fisico**: i controlli verificano una direzione di movimento e non un valore esatto, perché una simulazione non è mai ripetibile al millimetro.
- **Integrazione tra processi e linguaggi**: HTTP ⇄ ROS, Windows ⇄ Linux, JavaScript ⇄ Python.
- **Test isolati**: prima di ogni test il drone torna al centro, a fine suite viene fermato.

### Stack

`Playwright` · `ROS 2 Humble` · `Gazebo 11` · `Python` · `JavaScript` · `pytest` · `WSL2`

### Come è stato costruito

Questo è un progetto di studio: sto imparando come funzionano i simulatori di volo e come si testa un sistema fisico, non solo una pagina web. L'ho costruito **usando l'AI come assistente** (Cursor), che per me è parte normale del lavoro di oggi: la uso per esplorare tecnologie che non conosco ancora e per andare più veloce sulla parte meccanica.

Le decisioni però sono mie e verificate a mano: come separare il pilotaggio manuale dai test automatici, perché gli assert controllano una direzione invece di un valore esatto, come tarare le forze perché il drone resti governabile. Ogni cosa scritta qui l'ho eseguita davvero — la GIF sopra è una registrazione di una run reale dei test, non un mockup.

---

Il resto di questa pagina è la guida pratica: come installare, come pilotare il drone a mano e come lanciare i test.

---

## Com'è organizzato il progetto

```
drone-hil-automation-lab/
├─ e2e/                          test automatici Playwright (JavaScript)
│  ├─ drone-commands.spec.js     i 9 test e i loro assert
│  └─ support/                   client HTTP + regole dei controlli
├─ src/drone_simulator/
│  ├─ flight_control.py          forze, velocità massime, frenata, limiti dell'area
│  ├─ simulator.py               modello di volo offline (quello degli unit test)
│  ├─ gui.py                     simulatore 2D leggero, senza Gazebo
│  └─ ros/                       i nodi che parlano con Gazebo
│     ├─ bridge_server.py        il ponte: API HTTP ⇄ ROS
│     ├─ manual_control.py       tastiera ⇄ ROS, per volare a mano
│     └─ boundary_guard.py       riporta al centro il drone se esce dall'area
├─ scripts/                      comandi di avvio (.ps1 per Windows, .sh per Linux)
├─ gazebo/worlds/drone_lab.world il mondo 3D: drone, prato, alberi, capannone, recinzione
├─ tests/                        unit test pytest
├─ Dockerfile                    immagine con ROS 2, Gazebo e il ponte, headless
├─ docker/entrypoint.sh          avvia il mondo e poi il ponte, nell'ordine giusto
├─ docker-compose.yml            un comando per avere il drone in ascolto sulla 8765
└─ docs/                         demo e guida di installazione di ROS/Gazebo
```

---

## Cosa serve installato

| Cosa | Dove gira | Serve per |
|---|---|---|
| Windows 10/11 con WSL2 + Ubuntu 22.04 | — | far girare Linux dentro Windows |
| ROS 2 Humble + Gazebo 11 | dentro Ubuntu 22.04 | il mondo 3D e il drone |
| Python 3.10+ | Windows | i test veloci di logica |
| Node.js | Windows | i test automatici Playwright |

Prima installazione di Gazebo/ROS (una volta sola):

```powershell
wsl --install -d Ubuntu-22.04
wsl -d Ubuntu-22.04 -u root -- bash -lc "bash /mnt/c/Drone-HIL-Automation-Lab/scripts/install_real_gazebo.sh"
```

Dipendenze dei test (una volta sola):

```powershell
cd C:\Drone-HIL-Automation-Lab
npm install
python -m pip install -r requirements.txt
```

La guida dettagliata di ROS/Gazebo è in [docs/REAL_GAZEBO_SETUP.md](docs/REAL_GAZEBO_SETUP.md).

---

## Provarlo con Docker

Se vuoi solo provare i test, o vedere il programma girare, non devi installare ROS e Gazebo: sono già dentro l'immagine. Servono solo **Docker e Node**.

```powershell
git clone https://github.com/ForMat90/drone-hil-automation-lab.git
cd drone-hil-automation-lab
npm install
docker compose up -d --build     # la prima volta scarica ROS e Gazebo: qualche minuto
npx playwright test
docker compose down
```

Il comando di avvio ritorna solo quando il container è `healthy`, che vuol dire che Gazebo ha caricato il mondo e il drone risponde. Per controllarlo a mano:

```powershell
npm run drone:pose     # {"x": 0.0, "y": 0.0, "z": 3.0, ...} = il drone c'è
npm run drone:logs     # i log di Gazebo e del ponte, se qualcosa non torna
```

La prova vera che funziona sono i nove test verdi di `npx playwright test`.

Il container pubblica il ponte su `http://127.0.0.1:8765`, lo stesso indirizzo che i test usano quando Gazebo gira in WSL: i test sono gli stessi file, non c'è una variante per Docker.

Di base Gazebo gira headless, quindi **non si vede la finestra 3D**: i nove test passano e il risultato lo leggi nel terminale. Su Windows però c'è un override che aggancia il canale grafico di WSLg e apre anche la finestra, così vedi il drone muoversi mentre i test girano:

```powershell
npm run drone:up:gui
npx playwright test
```

Al container non arriva nessuna GPU, quindi la scena è renderizzata in software: si vede bene, ma è più pesante della strada con WSL descritta nei tre passi qui sotto.

---

## 1) Avviare Gazebo (si fa sempre per primo)

```powershell
cd C:\Drone-HIL-Automation-Lab
.\scripts\run_gazebo_windows.ps1
```

Si apre la finestra 3D con il drone, il prato, gli alberi, il capannone e la recinzione arancione.
Lascia questo terminale aperto: se lo chiudi, Gazebo si chiude.

---

## 2) Pilotare il drone a mano

In un **secondo terminale**:

```powershell
cd C:\Drone-HIL-Automation-Lab
.\scripts\run_manual_control_windows.ps1
```

Tasti:

| Tasto | Cosa fa |
|---|---|
| `w` / `s` | avanti / indietro |
| `a` / `d` | sinistra / destra |
| `r` / `f` | sale / scende |
| `q` / `e` | ruota su sé stesso (yaw) |
| `x` | stop |
| `Ctrl+C` | esci dal controllo manuale |

Qui **non c'è nessun browser e nessun indirizzo web**: il programma legge il tasto e lo manda subito a Gazebo.

Se il drone esce dall'area o va troppo in alto, viene riportato automaticamente al centro.

---

## 3) Test automatici (il drone si muove da solo)

Lascia Gazebo aperto e **chiudi il controllo manuale** (`Ctrl+C`): se restano accesi tutti e due, si contendono i comandi e il drone fa cose strane.

In un terzo terminale:

```powershell
cd C:\Drone-HIL-Automation-Lab
npx playwright test
```

Guarda la finestra di Gazebo: il drone parte da solo, va a sinistra, a destra, avanti, indietro, su, giù e ruota.
Nel terminale vedi la lista dei test con ✓ o ✗.

Alla fine il drone viene fermato e riportato al centro. **Gazebo resta aperto**: lo chiudi tu quando vuoi.

Comandi utili:

```powershell
npx playwright test                          # tutti i test
npx playwright test -g "A:"                  # solo i test del comando A
npx playwright test --reporter=html          # report navigabile
```

---

## 4) Test veloci di logica (unit test)

Questi **non aprono Gazebo** e durano meno di un secondo:

```powershell
cd C:\Drone-HIL-Automation-Lab
python -m pytest
```

---

## Come parlano tra loro i pezzi

Qui sta il punto che confonde di più, quindi con calma.

Il problema: **Gazebo e ROS girano dentro Linux (WSL) e parlano "ROS"**, mentre **Playwright gira su Windows e parla HTTP**. Sono due mondi diversi, con due linguaggi diversi. Non possono chiamarsi direttamente.

La soluzione è la stessa che si usa tra microservizi: mettere in mezzo **un piccolo servizio con delle API**. Quel servizio è [src/drone_simulator/ros/bridge_server.py](src/drone_simulator/ros/bridge_server.py): riceve richieste HTTP e le ritrasmette a ROS.

```
  npx playwright test                    (Windows, JavaScript)
            │
            │  chiamate HTTP
            ▼
  http://127.0.0.1:8765                  <-- le API le abbiamo scritte noi
  src/drone_simulator/ros/bridge_server.py   (Linux/WSL, Python)
            │
            │  messaggi ROS
            ▼
  Gazebo: il drone si muove
```

### Le API che usano i test

| Chiamata | A cosa serve |
|---|---|
| `POST /api/hold` con `{ "command": "a" }` | tieni premuto il comando (come tenere giù il tasto) |
| `POST /api/release` | lascia il comando: il drone rallenta e si ferma |
| `GET /api/pose` | leggi dove si trova il drone (x, y, z, velocità, rotazione) |
| `POST /api/reset` | rimetti il drone al centro |

Esempio di un test, passo per passo:

1. il test chiama `POST /api/hold` con `a`;
2. il servizio traduce e pubblica una spinta verso sinistra sul canale ROS `/drone/gazebo_ros_force`;
3. Gazebo applica la spinta e il drone si sposta;
4. ogni 0,2 secondi il test chiama `GET /api/pose` e segna la posizione;
5. dopo 5 secondi chiama `POST /api/release`;
6. controlla i dati raccolti: «è andato davvero a sinistra?». Se sì il test passa.

### Due cose importanti

- **Playwright qui non apre nessun browser.** Di solito Playwright serve per testare siti web cliccando i bottoni; in questo progetto lo usiamo solo come strumento che fa chiamate API e scrive gli assert. Il "risultato" non si guarda in una pagina, si guarda in Gazebo e nei numeri della posizione.
- **L'indirizzo `http://127.0.0.1:8765` non è un sito.** È solo il ponte tra Windows e Linux: se lo apri nel browser ti risponde un JSON con l'elenco delle API. Il ponte **parte da solo** quando lanci i test (lo avvia [e2e/support/global-setup.js](e2e/support/global-setup.js)). Se vuoi avviarlo a mano: `.\scripts\run_bridge_windows.ps1`.

---

## Cosa verifichiamo davvero

### Test automatici su Gazebo — [e2e/drone-commands.spec.js](e2e/drone-commands.spec.js)

Prima di ogni test il drone viene riportato al centro, così un test non falsa quello dopo.
Ogni comando resta premuto **5 secondi**: abbastanza per vedere il movimento a occhio nella finestra 3D.

| Test | Cosa controlla |
|---|---|
| A / D: sinistra, destra | il drone si sposta di lato, nel verso giusto |
| W / S: avanti, indietro | il drone si sposta in avanti e indietro |
| R / F: su, giù | il drone cambia quota |
| A: arrivato a fine percorso torna al centro | spingendo fino al limite dell'area, il drone viene riportato al centro |
| rilascio: il drone si ferma | dopo aver lasciato il comando la velocità scende quasi a zero e non continua a scivolare |
| Q e E fanno ruotare il drone | il drone ruota su sé stesso (yaw) |

### Unit test — [tests/test_drone_simulator.py](tests/test_drone_simulator.py)

Controllano la logica pura, senza Gazebo: stati del drone (fermo, armato, decollo, volo, atterraggio, emergenza), decollo, atterraggio, stop di emergenza, i limiti dell'area e il fatto che un comando tenuto premuto si fermi al rilascio.

A ogni push su GitHub girano **entrambi i livelli**: gli unit test, e i test end-to-end contro il container Docker con Gazebo headless. È il badge in cima alla pagina.

---

## File chiave

| Percorso | A cosa serve |
|---|---|
| [scripts/run_gazebo_windows.ps1](scripts/run_gazebo_windows.ps1) | apre Gazebo dal terminale Windows |
| [scripts/run_manual_control_windows.ps1](scripts/run_manual_control_windows.ps1) | avvia il pilotaggio con la tastiera |
| [scripts/run_bridge_windows.ps1](scripts/run_bridge_windows.ps1) | avvia il ponte a mano (di solito non serve) |
| [scripts/run_gazebo_3d.sh](scripts/run_gazebo_3d.sh) | lo script Linux che lancia davvero Gazebo |
| [src/drone_simulator/ros/bridge_server.py](src/drone_simulator/ros/bridge_server.py) | il ponte: API HTTP ⇄ ROS, porta 8765 |
| [src/drone_simulator/ros/manual_control.py](src/drone_simulator/ros/manual_control.py) | legge i tasti e manda le spinte a ROS |
| [src/drone_simulator/flight_control.py](src/drone_simulator/flight_control.py) | forze dei comandi, velocità massima, frenata, limiti dell'area |
| [e2e/drone-commands.spec.js](e2e/drone-commands.spec.js) | i test automatici e i loro controlli |
| [e2e/support/drone-api.js](e2e/support/drone-api.js) | le chiamate al ponte: tieni premuto, leggi posizione, reset |
| [e2e/support/flight-checks.js](e2e/support/flight-checks.js) | le regole dei controlli: "si è mosso verso sinistra?", "è fermo?" |
| [e2e/support/global-setup.js](e2e/support/global-setup.js) | prima dei test: trova o avvia il ponte |
| [playwright.config.js](playwright.config.js) | configurazione dei test (timeout, ordine, report) |
| [tests/test_drone_simulator.py](tests/test_drone_simulator.py) | unit test della logica |
| [gazebo/worlds/drone_lab.world](gazebo/worlds/drone_lab.world) | il mondo 3D |
| [Dockerfile](Dockerfile) · [docker/entrypoint.sh](docker/entrypoint.sh) | ROS 2, Gazebo e il ponte in un'immagine headless |
| [.github/workflows/tests.yml](.github/workflows/tests.yml) | CI: unit test, e test end-to-end col container |

Se vuoi cambiare quanto è veloce o reattivo il drone, tocca **un solo file**: `src/drone_simulator/flight_control.py`. Contiene due gruppi di impostazioni: quelle "a pressione continua" usate dal ponte e dai test, e quelle "a impulso" usate dalla tastiera, che hanno bisogno di una spinta più forte perché ogni tasto premuto vale una spinta sola.

---

## Extra

**Protezione automatica dell'area** (facoltativa, in un altro terminale). Serve solo se tieni Gazebo aperto senza né tastiera né ponte, perché quei due si riportano già al centro da soli:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "source /opt/ros/humble/setup.bash; cd /mnt/c/Drone-HIL-Automation-Lab/src; python3 -m drone_simulator.ros.boundary_guard"
```

**Simulatore 2D leggero** (finestra Python, niente Gazebo, utile per provare la logica di volo):

```powershell
python run_simulator.py
```

---

## Se qualcosa non va

| Sintomo | Causa e rimedio |
|---|---|
| I test dicono che Gazebo non è aperto | apri prima `.\scripts\run_gazebo_windows.ps1` e aspetta la finestra 3D |
| La finestra di Gazebo si chiude subito con un errore di grafica | rilancia lo script: chiude da solo i processi rimasti appesi |
| Il drone non risponde ai tasti | Gazebo non è aperto, oppure stai scrivendo nel terminale sbagliato |
| Il drone fa movimenti strani durante i test | hai lasciato aperto anche il controllo manuale: chiudilo con `Ctrl+C` |
| Playwright chiede di installare un browser | non serve: questi test non usano il browser. Assicurati di lanciare `npx playwright test` dalla cartella del progetto |

---

## Note sui test e possibili miglioramenti

**Come sono fatti i test, in breve.** Non controllano "un numero esatto", perché una simulazione fisica non dà mai due volte lo stesso risultato. Controllano una **direzione**: dopo aver tenuto premuto `a`, il drone deve essersi spostato verso sinistra di almeno qualche decina di centimetri. Questo li rende stabili e non fastidiosi da mantenere. La posizione viene campionata durante tutto il movimento, non solo alla fine, così il test non fallisce se nel frattempo il drone è stato riportato al centro.

Cose che si possono aggiungere per rendere il progetto più solido:

- **Un test che fallisce apposta**, per essere sicuri che i controlli funzionino davvero e non passino sempre.
- **Test di collisione**: verificare che il drone non attraversi il capannone o gli alberi.
- **Test di atterraggio sulla piazzola**, con tolleranza sulla precisione.
- **Cache dell'immagine in CI**: oggi il passaggio più lento della pipeline è costruire l'immagine, perché si riscarica ROS e Gazebo ogni volta. Si può pubblicare l'immagine su un registry e riusarla.
- **Un solo comando di avvio anche per la parte con la finestra 3D**: con Docker basta `docker compose up`, ma la strada WSL vuole ancora tre terminali.
- **Un autopilota vero (PX4/SITL)** se in futuro servisse simulare anche il firmware di volo: più realistico, ma molto più pesante da installare.
