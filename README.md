# Algoritmo de Apuestas Deportivas - Dixon-Coles & Value Betting

Sistema estadístico para el cálculo de probabilidades reales de partidos de fútbol y detección de **Apuestas con Valor (+EV / Value Bets)** para casas de apuestas como **Betano**.

---

## 🚀 Estructura del Proyecto

```
c:\APUESTAS\
│── data/                      # Almacenamiento de datos de partidos
│   └── historical/            # Archivos CSV descargados automáticamente
│── src/                       # Módulos del sistema
│   ├── data_loader.py         # Descarga y limpieza de datos (football-data.co.uk)
│   ├── poisson_model.py       # Modelo Dixon-Coles (Poisson Bivariado vectorizado)
│   ├── value_finder.py        # Detector de cuotas con EV positivo (+EV)
│   └── bankroll.py            # Cálculo de stake óptimo (Criterio de Kelly Fraccionado)
│── main.py                    # Pipeline de entrenamiento y evaluación por liga
│── predict_custom.py          # Analizador de partidos individuales con cuotas de Betano
│── requirements.txt           # Librerías de Python requeridas
└── README.md                  # Documentación
```

---

## 🛠️ Instalación y Requisitos

1. **Requisitos de Python:**
   Asegúrate de contar con Python 3.10+ y las librerías necesarias:
   ```bash
   pip install -r requirements.txt
   ```

---

## 📖 Instrucciones de Uso

### 1. Evaluar una Liga Completa
Para descargar datos históricos de las últimas 3 temporadas, entrenar el modelo y buscar Value Bets en una liga:
```bash
python main.py SP1   # La Liga (España)
python main.py E0    # Premier League (Inglaterra)
python main.py I1    # Serie A (Italia)
python main.py D1    # Bundesliga (Alemania)
python main.py F1    # Ligue 1 (Francia)
```

### 2. Analizar un Partido Individual con Cuotas de Betano
Para ingresar las cuotas ofrecidas por **Betano** para un partido específico y calcular si hay valor:
```bash
python predict_custom.py "Real Madrid" "Barcelona" "SP1"
```

---

## 📐 Fundamento Matemático

1. **Modelo Dixon-Coles:**
   Calcula la fuerza de ataque \(\alpha_i\) y la debilidad defensiva \(\beta_j\) de cada equipo junto con el factor de ventaja de localía (\(\gamma_{home}\)). Corrige la subestimación de marcadores bajos (0-0, 1-0, 0-1, 1-1) mediante el parámetro \(\rho\).
   $$\lambda = \alpha_{local} \times \beta_{visita} \times \gamma_{home}$$
   $$\mu = \alpha_{visita} \times \beta_{local}$$

2. **Cálculo de Valor Esperado (EV):**
   $$EV\% = (P_{modelo} \times \text{Cuota}_{Betano} - 1) \times 100$$
   Una apuesta se considera **Value Bet** si el \(EV\% > 0\).

3. **Gestión de Banca (Quarter Kelly):**
   $$f^* = \frac{P_{modelo} \times \text{Cuota} - 1}{\text{Cuota} - 1} \times 0.25$$
   Evita sobre-exponer la banca limitando el stake máximo al 5% por apuesta.
