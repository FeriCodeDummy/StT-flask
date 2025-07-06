# Glavno Zaledje Medicinskega Diktafona
## Kazalo
- [O Zaledju](#o-zaledju)
- [Namestitev](#namestitev)
- [Struktura](#struktura)

# O zaledju

Zaledje za vspostavljanje zavarovane komunikacije med uporabiki, 
zaledjem za transkripcijo in podatkovno bazo. Podatki na tem zaledju se ne shranijo trajno in so izbrisane ko je transkripcija neke anamneze pripravljena.

Omogoča: 
- Sprejem posnetkov od več uporabnikov hkrati.
- Pošiljanje posnetkov zaledju za traskripcijo.
- Sprejem in shranjevanje transkribiranih vsebin.
- Dostava anamnez od podatkovne baze do uporabnika.

# Namestitev

Za prenos mape in namestitev prvič naredite
```
github clone https://github.com/FeriCodeDummy/StT-flask
```

Za zagon zaledja uporabite
```
python server.py
```


# Struktura

```
-StT-queue          
--uploads           
---...              - začasni podatki
--gdpr_auth.py      - šifriranje ene del anamneze
--mq-server         - podsistem za čakalno vrsto
--queue-stt         - pošiljanje transkripcij po vrsti
-dbm.py             - seznam poizvedb za podatkovno bazo
-gdpr_auth.py       - šifriranje anamnez
-server.py          - komunikacija med zaledjem, uporabniki in pb
```
