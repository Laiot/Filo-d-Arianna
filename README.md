# Filum-Ariadnae

Arianna è un progetto realizzato da studenti del Politecnico di Milano in collaborazione con la regione Lombardia per sensibilizzare studenti di scuola secondaria di primo e secondo grado riguardo le dinamiche della violenza, fisica e non, all'interno di una relazione di coppia tramite la digitalizzazione di un libro-game. Questa repo serve a mettere in evidenza il mio lavoro, ovvero:

  - Creare una catena di Markov.
  - Usare la catena per parsare le pagine (HTML) del libro.
  - Creare il server tramite la libreria python Flask. Può essere assegnato una diversa probabilità alle pagine.
  - Simulare così una randomicità tra gli eventi descritti nel libro.

### Sviluppo
La catena di Markov è stata realizzata creando una classe nell'omonimo file (MarkovChain.py) e testando il parsing con una generazione procedurale di grafi. Il file non è al momento atto a mostrare questa procedura (creerò un branch apposito per metterlo in evidenza).
Il file main.py mostra il routing e il modo in cui l'iterazione tra le pagine del libro avviene, grazie alla catena.

### Progetto
Il progetto è stato realizzato dall'alunno Carmelo Sarta (10524131) sotto il tutoraggio del docente Agosta Giovanni per il corso Progetto di Ingegneria Informatica (089020).
