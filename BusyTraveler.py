from __future__ import print_function
from ortools.linear_solver import pywraplp
from landmarksHelper import recover_distances, recover_landmarks
import random

# impongo il massimo tempo di computazione a 60 secondi
MAX_COMPUTING_TIME = 30
NUM_THREADS = 8

n = 0
V = []
popolarita = []
monumenti = []
D = []
policy = "Tutti"

def set_up(pol, numMon):

  global n, V, popolarita, monumenti, D, policy

  # nome dei monumenti da visitare
  monumenti = recover_landmarks()

  #print(len(monumenti))
  # matrice delle distanze, per semplificare i test assumo in tale istanza che
  # la distanza associata all'arco Xij è uguale alla distanza associata all'arco Xji
  # (le distanza sono espresse in termini di tempo)

  distanze_info = recover_distances()

  curr = distanze_info[0]["Start"]
  line = []
  distanze = []
  for i in range(0, len(distanze_info)):
    if distanze_info[i]["Transport"] == "driving":
      break
    if curr != distanze_info[i]["Start"]:
      distanze.append(line)
      line = []
      curr = distanze_info[i]["Start"]
    else:
      line.append(int(distanze_info[i]["Seconds"]))

  distanze.append([])

  random.seed(a="paperino", version=2)

  # vettore di popolarità dei monumenti del grafo (il primo elemento
  # è la popolarità del nodo utente, pari a zero. Inserito per semplificare
  # la gestione degli indici nell'implementazione)
  popolarita = [random.randint(0, 100) for i in range(0, len(monumenti))]

  # vettore di distanze dall'utente ai nodi
  # (da incorporare nella matrice delle distanze)
  du = [random.randint(100, 500) for i in range(0, len(monumenti))]

  # aggiungo distanze dall'utente ai nodi
  V = set(range(len(distanze)))
  D = [[0 if i == j
        else distanze[i][j-i-1] if j > i
        else distanze[j][i-j-1]
        for j in V] for i in V]

  cp = du[:]
  cp.insert(0,0)
  D.insert(0,cp)
  for i in range(1, len(V)+1):
    D[i].insert(0, cp[i])

  # !!!!!!! qui in base alla strategia di restingimento dei monumenti
  # ridimensiono la matrice D


  # definisco l'insieme dei nodi e la sua cardinalità
  V = set(range(1, len(monumenti)))

  # aggiungo all'insieme dei nodi, il nodo utente
  V.add(0)

  # cardinalità dell'insieme dei nodi
  n = len(V)


# tempo massimo a disposizione dell'utente
def BusyTraveler(T):

  # definisco il modello ed il suo nome
  solver = pywraplp.Solver('BusyTraveler', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)



  # definizione delle variabili X(i-j)
  infinity = solver.infinity()
  x = []
  for i in V:
    x.append([])
    for j in V:
      x[i].append(solver.IntVar(0, 1, "X({}-{})".format(i,j)))

  # definizione variabili Y(i)
  y = [solver.IntVar(0, infinity, "Y({})".format(i)) for i in V]

  # definizione variabili H(i)
  h = [solver.IntVar(0, 1, "H({})".format(i)) for i in V]




  # Vincolo di tipo (1)
  for i in V:
    solver.Add(solver.Sum(x[i][j]*D[i][j] for j in V for i in V) <= T)

  # Vincolo di tipo (2)
  for j in V:
    solver.Add(solver.Sum(x[i][j] for i in V - {j}) <= 1)

  # Vincolo di tipo (3)
  for i in V:
      solver.Add(solver.Sum(x[i][j] for j in V - {i}) <= 1)

  # Vincolo di tipo (4)
  solver.Add(y[0] == 1)

  # Vincolo di tipo (5)
  for i in V - {0}:
      solver.Add(y[i] - solver.Sum((n+1)*x[j][i] for j in V) <= 0)

  # Vincolo di tipo (6)
  for i in V:
    for j in V:
      solver.Add(x[i][j] - y[i] <= 0)

  # Vincolo di tipo (7)
  for i in V:
    for j in V:
      solver.Add(y[j] >= y[i] + 1 - (n+1)*(1-x[i][j]))

  # Vincolo di tipo (8)
  for i in V:
    solver.Add(h[i] <= y[i])



  # funzione obiettivo
  #objective = solver.Objective()
  solver.Maximize(solver.Sum(h[i]*popolarita[i] for i in V))

  # TEMPO LIMITE
  #solver.set_time_limit(MAX_COMPUTING_TIME*1000)
  # numero di thread per il solver
  solver.SetNumThreads(NUM_THREADS)

  # optimizing
  status = solver.Solve()

  # stampo la soluzione
  if status == pywraplp.Solver.OPTIMAL:
    solved = "Si"
    ub = solver.Objective().Value()
    lb = ub
    f.write('Valore della funzione obbiettivo = {}\n'.format(lb))

    mons = []
    for i in V-{0}:
      if(y[i].solution_value() != 0):
        mons.append((i, y[i].solution_value()))
    mons.sort(key=lambda x:x[1])

    f.write("Percorso trovato con t = {}:\n".format(T))
    f.write("Utente")

    for mon in mons:
        f.write("----->{}".format(monumenti[mon[0]]))
    f.write(".\n")

    f.write('Problema risolto in {} minuti\n'.format((solver.wall_time()/1000)/60))

  else:
    lb = solver.Objective().Value()
    ub = solver.Objective().BestBound()
    solved = "No"
    f.write('Il problema non ha soluzione ottima entro {} secondi\n'.format(MAX_COMPUTING_TIME))
    f.write('Lower Bound = {}\n'.format(lb))
    f.write('Upper Bound = {}\n'.format(ub))

  f.write("--------------------\n\n")

  # scrivo risultati sul csv
  csv_results(T, lb, ub, solved, len(monumenti))

  ## TODO:
  # se non ho risolto in un ora scelgo una policy di ridimensionamento dei monumenti


csv_filename = "BusyTravelerResults.csv"
def csv_results(t, lb, up, solved, numMon):
  import os

  
  # if the file does not exist
  if (not os.path.exists(csv_filename)):
    f = open(csv_filename, "w")
    f.write("Tempo Del Viaggiatore, Lower Bound, Upper Bound, Risolto In 1 h, Monumenti Considerati, Politica Selezione Monumenti\n")
  else:
    f = open(csv_filename, "a")
  f.write(str(t)+ ", "+ str(lb)+ ", "+ str(up)+ ", "+ str(solved)+ ", "+ str(numMon)+ ", "+ str(policy)+ "\n")
  f.close()


f = open("ResultsBusyTraveller.txt", "a")
if __name__ == "__main__":

  # TODO automatizzare tesing
  # inizio con tutti i nodi, poi restringo se necessario
  # dentro il metodo BusyTraveller
  set_up("All", 500)
  T = 10000
  BusyTraveler(T)
  f.close()
