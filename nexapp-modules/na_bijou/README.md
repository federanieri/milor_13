# na_bijou

- Se le mail non vengono intercettate, verificare che non siano state aperte.
- Nel caso in cui una mail viene aperta per sbaglio allora è necessario re-inviarla a edi@milor.it

Setup per funzionamento modulo

1. Andare su interfaccia Odoo
2. Creare un nuovo progetto, 'EDI'.
3. Impostare come mail relativa al progetto 'edi'; [il dominio deve essere @milor.it e dovrebbe già
   essere impostato, nel caso così non fosse bisogna entrare nei parametri di sistema e modificare
   il dominio corrente] così facendo verrà creato l'Alias che si occuperà di intercettare le mail da
   edi@milor.it.
4. Le mail vengono ricevute sottoforma di Task all'interno del nuovo progetto e negli allegati si
   potrà trovare il file .cde necessario per il sync nel modulo Bijou.

# formattazione file .bl

In caso di problemi, fare riferimento a questo
link: https://stackoverflow.com/questions/47178459/replace-crlf-with-lf-in-python-3-6