============
na_milor_sale_analysis
============

    BRANCH 13.0

**Funzionalità**

 Questo modulo è necessario per la revisione del flusso dei child PO
- Sovrascritta la funzione _autopopolate del modulo syd_custom, rendendola inattiva.
- Durante la create se l'ordine ha un ordine padre prenderà il nome di quest'ultimo più /C ed il numero progressivo.
- Un ordine, se figlio di un altro ordine, al primo salvataggio tutte le righe inserite verrano cancellate e verranno aggiunte quelle del padre.
- Aggiunto un pulsante che permette di ricaricare le righe d'ordine sulla base del parente inserito.


