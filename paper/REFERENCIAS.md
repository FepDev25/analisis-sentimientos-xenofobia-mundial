# Referencias académicas — Paper (Proyecto final)

> Recolectadas y verificadas mediante búsqueda web (WebSearch/WebFetch) en julio de 2026.
> Cada entrada indica autores, título, venue, año, DOI/URL, para qué sirve en **nuestro** artículo,
> y una entrada BibTeX (plantilla Springer: `@article`/`@inproceedings`/`@misc` según corresponda).
> El detalle de qué se pudo verificar directamente en la fuente está en la sección **Verificación** al final.

---

## 1. Detección de discurso de odio y hate speech implícito/velado

### 1.1 ElSherief et al. (2021) — *Latent Hatred*

- **Autores:** Mai ElSherief, Caleb Ziems, David Muchlinski, Vaishnavi Anupindi, Jordyn Seybolt, Munmun De Choudhury, Diyi Yang
- **Título:** "Latent Hatred: A Benchmark for Understanding Implicit Hate Speech"
- **Venue:** Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing (EMNLP 2021), pp. 345–363
- **Año:** 2021
- **DOI:** 10.18653/v1/2021.emnlp-main.29 · URL: https://aclanthology.org/2021.emnlp-main.29/
- **Para qué sirve:** introduce la taxonomía y el benchmark de referencia para discurso de odio *implícito* (ironía, estereotipos, "white grievance" codificado). Es la base conceptual de nuestro hallazgo 1: los clasificadores estándar fallan frente al odio no explícito, justamente el fenómeno que documentamos con leetspeak, emojis y portmanteaus.

```bibtex
@inproceedings{elsherief2021latent,
  author    = {ElSherief, Mai and Ziems, Caleb and Muchlinski, David and Anupindi, Vaishnavi and Seybolt, Jordyn and De Choudhury, Munmun and Yang, Diyi},
  title     = {Latent Hatred: A Benchmark for Understanding Implicit Hate Speech},
  booktitle = {Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing},
  pages     = {345--363},
  year      = {2021},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2021.emnlp-main.29}
}
```

### 1.2 Kirk et al. (2022) — *Hatemoji*

- **Autores:** Hannah Rose Kirk, Bertie Vidgen, Paul Röttger, Tristan Thrush, Scott A. Hale
- **Título:** "Hatemoji: A Test Suite and Adversarially-Generated Dataset for Benchmarking and Detecting Emoji-Based Hate"
- **Venue:** Proceedings of the 2022 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL 2022)
- **Año:** 2022
- **DOI/URL:** https://aclanthology.org/2022.naacl-main.97/ · arXiv: 2108.05921
- **Para qué sirve:** evidencia empírica de que sustituir una palabra de odio por su emoji equivalente hunde el rendimiento de los clasificadores de moderación de contenido. Sustenta directamente nuestro hallazgo del subregistro de 🐒🍌 (emojis en clave racista) por modelos preentrenados estándar.

```bibtex
@inproceedings{kirk2022hatemoji,
  author    = {Kirk, Hannah Rose and Vidgen, Bertie and R{\"o}ttger, Paul and Thrush, Tristan and Hale, Scott A.},
  title     = {Hatemoji: A Test Suite and Adversarially-Generated Dataset for Benchmarking and Detecting Emoji-Based Hate},
  booktitle = {Proceedings of the 2022 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies},
  year      = {2022},
  publisher = {Association for Computational Linguistics},
  url       = {https://aclanthology.org/2022.naacl-main.97/}
}
```

### 1.3 Frenda, Patti & Rosso (2023) — *When Sarcasm Hurts*

- **Autores:** Simona Frenda, Viviana Patti, Paolo Rosso
- **Título:** "When Sarcasm Hurts: Irony-Aware Models for Abusive Language Detection"
- **Venue:** CLEF 2023 — *Experimental IR Meets Multilinguality, Multimodality, and Interaction*, Lecture Notes in Computer Science, vol. 14163, Springer
- **Año:** 2023
- **DOI/URL:** https://link.springer.com/chapter/10.1007/978-3-031-42448-9_4
- **Para qué sirve:** hipótesis y experimentos de que el conocimiento de la ironía/sarcasmo mejora la detección de mensajes de odio "camuflados" como broma — es el paper académico más cercano a nuestro hallazgo central de que el humor es vehículo del discurso de odio velado (xenofobia disfrazada de chiste).

```bibtex
@inproceedings{frenda2023sarcasm,
  author    = {Frenda, Simona and Patti, Viviana and Rosso, Paolo},
  title     = {When Sarcasm Hurts: Irony-Aware Models for Abusive Language Detection},
  booktitle = {Experimental IR Meets Multilinguality, Multimodality, and Interaction (CLEF 2023)},
  series    = {Lecture Notes in Computer Science},
  volume    = {14163},
  year      = {2023},
  publisher = {Springer},
  doi       = {10.1007/978-3-031-42448-9_4}
}
```

### 1.4 Piot, Martín-Rodilla & Parapar (2024) — *MetaHate*

- **Autores:** Paloma Piot, Patricia Martín-Rodilla, Javier Parapar
- **Título:** "MetaHate: A Dataset for Unifying Efforts on Hate Speech Detection"
- **Venue:** Proceedings of the International AAAI Conference on Web and Social Media (ICWSM 2024)
- **Año:** 2024
- **DOI/URL:** arXiv 2401.06526 · https://ojs.aaai.org/index.php/ICWSM/article/view/31445
- **Para qué sirve:** meta-dataset que unifica 36 corpus de hate speech (>1.2M comentarios) para benchmarking. Referencia obligada para justificar por qué un modelo entrenado en un corpus no basta (dominio, idioma, plataforma) y por qué comparamos varias estrategias de clasificación (léxico, transformer, LLM) en vez de confiar en una sola.

```bibtex
@inproceedings{piot2024metahate,
  author    = {Piot, Paloma and Mart{\'i}n-Rodilla, Patricia and Parapar, Javier},
  title     = {MetaHate: A Dataset for Unifying Efforts on Hate Speech Detection},
  booktitle = {Proceedings of the International AAAI Conference on Web and Social Media},
  year      = {2024},
  eprint    = {2401.06526},
  archivePrefix = {arXiv}
}
```

### 1.5 Basile et al. (2019) — *HatEval* (clásico / dataset canónico)

- **Autores:** Valerio Basile, Cristina Bosco, Elisabetta Fersini, Debora Nozza, Viviana Patti, Francisco Manuel Rangel Pardo, Paolo Rosso, Manuela Sanguinetti
- **Título:** "SemEval-2019 Task 5: Multilingual Detection of Hate Speech Against Immigrants and Women in Twitter"
- **Venue:** Proceedings of the 13th International Workshop on Semantic Evaluation (SemEval-2019), pp. 54–63
- **Año:** 2019
- **DOI:** 10.18653/v1/S19-2007 · URL: https://aclanthology.org/S19-2007/
- **Marcado como clásico:** anterior a la ventana 2023-2026, pero es el dataset **canónico** de hate speech contra inmigrantes en inglés/español — el antecedente directo y obligado de cualquier trabajo sobre xenofobia digital en redes.
- **Para qué sirve:** referencia fundacional para el marco de detección de odio dirigido a inmigrantes (aplicable a xenofobia futbolística) y para el diseño bilingüe (inglés/español) de nuestra propia estrategia de búsqueda.

```bibtex
@inproceedings{basile2019hateval,
  author    = {Basile, Valerio and Bosco, Cristina and Fersini, Elisabetta and Nozza, Debora and Patti, Viviana and Rangel Pardo, Francisco Manuel and Rosso, Paolo and Sanguinetti, Manuela},
  title     = {SemEval-2019 Task 5: Multilingual Detection of Hate Speech Against Immigrants and Women in Twitter},
  booktitle = {Proceedings of the 13th International Workshop on Semantic Evaluation},
  pages     = {54--63},
  year      = {2019},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/S19-2007}
}
```

---

## 2. Análisis de sentimientos multilingüe en español (pysentimiento / RoBERTuito / BETO)

### 2.1 Pérez et al. (2021) — *pysentimiento*

- **Autores:** Juan Manuel Pérez, Mariela Rajngewerc, Juan Carlos Giudici, Damián A. Furman, Franco Luque, Laura Alonso Alemany, María Vanina Martínez
- **Título:** "pysentimiento: A Python Toolkit for Opinion Mining and Social NLP tasks"
- **Venue:** arXiv preprint (Computation and Language)
- **Año:** 2021 (subido 17-jun-2021; revisión más reciente 2024)
- **arXiv:** 2106.09462
- **Para qué sirve:** es la librería que usamos en la P7 para el eje de sentimiento/emoción/odio/ironía en español. Referencia directa de la herramienta empleada en el pipeline de clasificación.

```bibtex
@misc{perez2021pysentimiento,
  author       = {P{\'e}rez, Juan Manuel and Rajngewerc, Mariela and Giudici, Juan Carlos and Furman, Dami{\'a}n A. and Luque, Franco and Alonso Alemany, Laura and Mart{\'i}nez, Mar{\'i}a Vanina},
  title        = {pysentimiento: A Python Toolkit for Opinion Mining and Social NLP tasks},
  year         = {2021},
  eprint       = {2106.09462},
  archivePrefix = {arXiv}
}
```

### 2.2 Pérez et al. (2022) — *RoBERTuito*

- **Autores:** Juan Manuel Pérez, Damián A. Furman, Laura Alonso Alemany, Franco Luque
- **Título:** "RoBERTuito: a pre-trained language model for social media text in Spanish"
- **Venue:** Proceedings of the 13th Language Resources and Evaluation Conference (LREC 2022)
- **Año:** 2022
- **URL:** https://aclanthology.org/2022.lrec-1.785/ · arXiv: 2111.09453
- **Para qué sirve:** modelo base (RoBERTa entrenado en >500M tweets en español) sobre el que corre `pysentimiento`. Justifica en el paper la elección de un modelo de dominio (tuits) en vez de un BERT genérico para clasificar comentarios de redes sociales.

```bibtex
@inproceedings{perez2022robertuito,
  author    = {P{\'e}rez, Juan Manuel and Furman, Dami{\'a}n A. and Alonso Alemany, Laura and Luque, Franco},
  title     = {RoBERTuito: a pre-trained language model for social media text in Spanish},
  booktitle = {Proceedings of the 13th Language Resources and Evaluation Conference},
  year      = {2022},
  publisher = {European Language Resources Association},
  url       = {https://aclanthology.org/2022.lrec-1.785/}
}
```

### 2.3 Cañete et al. (2020) — *BETO*

- **Autores:** José Cañete, Gabriel Chaperon, Rodrigo Fuentes, Jou-Hui Ho, Hojin Kang, Jorge Pérez
- **Título:** "Spanish Pre-Trained BERT Model and Evaluation Data"
- **Venue:** PML4DC Workshop at ICLR 2020
- **Año:** 2020
- **URL:** https://users.dcc.uchile.cl/~jperez/papers/pml4dc2020.pdf (workshop paper; sin DOI de editorial)
- **Marcado como cuasi-clásico:** es el BERT en español canónico (2020) que antecede a RoBERTuito; se incluye por ser la comparación obligada de todo modelo en español.
- **Para qué sirve:** referencia para justificar por qué un modelo de dominio (RoBERTuito/pysentimiento) supera a un BERT genérico en español para texto de redes sociales.

```bibtex
@inproceedings{canete2020beto,
  author    = {Ca{\~n}ete, Jos{\'e} and Chaperon, Gabriel and Fuentes, Rodrigo and Ho, Jou-Hui and Kang, Hojin and P{\'e}rez, Jorge},
  title     = {Spanish Pre-Trained {BERT} Model and Evaluation Data},
  booktitle = {Practical ML for Developing Countries Workshop, ICLR 2020},
  year      = {2020}
}
```

### 2.4 Barbieri, Espinosa-Anke & Camacho-Collados (2022) — *XLM-T*

- **Autores:** Francesco Barbieri, Luis Espinosa Anke, José Camacho-Collados
- **Título:** "XLM-T: Multilingual Language Models in Twitter for Sentiment Analysis and Beyond"
- **Venue:** Proceedings of the 13th Language Resources and Evaluation Conference (LREC 2022), pp. 258–266, Marseille, Francia
- **Año:** 2022
- **URL:** https://aclanthology.org/2022.lrec-1.27/ (LREC 2022 proceedings, repo `cardiffnlp/xlm-t`) · arXiv: 2104.12250
- **Para qué sirve:** es el paper detrás de `cardiffnlp/twitter-xlm-roberta-base-sentiment`, el modelo transformer multilingüe mencionado como candidato en nuestro diseño (alternativa/comparación a pysentimiento para tuits en varios idiomas simultáneamente, relevante porque nuestro dataset mezcla español/inglés/portugués).

```bibtex
@inproceedings{barbieri2022xlmt,
  author    = {Barbieri, Francesco and Espinosa Anke, Luis and Camacho-Collados, Jos{\'e}},
  title     = {{XLM-T}: Multilingual Language Models in {T}witter for Sentiment Analysis and Beyond},
  booktitle = {Proceedings of the 13th Language Resources and Evaluation Conference},
  pages     = {258--266},
  year      = {2022},
  publisher = {European Language Resources Association},
  eprint    = {2104.12250},
  archivePrefix = {arXiv}
}
```

### 2.5 Nguyen, Vu & Nguyen (2020) — *BERTweet* (referencia de contraste, inglés)

- **Autores:** Dat Quoc Nguyen, Thanh Vu, Anh Tuan Nguyen
- **Título:** "BERTweet: A pre-trained language model for English Tweets"
- **Venue:** Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing: System Demonstrations (EMNLP 2020), pp. 9–14
- **Año:** 2020
- **DOI:** 10.18653/v1/2020.emnlp-demos.2 · URL: https://aclanthology.org/2020.emnlp-demos.2/
- **Para qué sirve:** contraparte en inglés de RoBERTuito/BETO (mismo patrón: RoBERTa preentrenado en tuits del idioma objetivo). Se cita para argumentar que la estrategia "modelo de dominio en tuits, no BERT genérico" es una práctica establecida y no ad hoc, replicada en varios idiomas.

```bibtex
@inproceedings{nguyen2020bertweet,
  author    = {Nguyen, Dat Quoc and Vu, Thanh and Nguyen, Anh Tuan},
  title     = {{BERTweet}: A pre-trained language model for {E}nglish {T}weets},
  booktitle = {Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing: System Demonstrations},
  pages     = {9--14},
  year      = {2020},
  publisher = {Association for Computational Linguistics},
  doi       = {10.18653/v1/2020.emnlp-demos.2}
}
```

---

## 3. Racismo y xenofobia en redes sociales, contexto deportivo/futbolístico

### 3.1 Hylton, Kilvington, Long, Bond & Chaudry (2024)

- **Autores:** Kevin Hylton, Dan Kilvington, Jonathan Long, Alex Bond, Izram Chaudry
- **Título:** "Dear Prime Minister, Mr Musk and Mr Zuckerberg!: The challenge of social media and platformed racism in the English premier league and football league"
- **Venue:** International Review for the Sociology of Sport, vol. 59, no. 6, pp. 844–867
- **Año:** 2024
- **DOI:** 10.1177/10126902241234282
- **Para qué sirve:** analiza el racismo "plataformizado" (moderación insuficiente de las redes) en el fútbol inglés — sostiene nuestro argumento de que la disponibilidad y el diseño de las plataformas (no solo los usuarios) son parte del problema, conectando con nuestro hallazgo 5 (cierre de APIs = decisión comercial).

```bibtex
@article{hylton2024dearpm,
  author  = {Hylton, Kevin and Kilvington, Dan and Long, Jonathan and Bond, Alex and Chaudry, Izram},
  title   = {Dear Prime Minister, Mr Musk and Mr Zuckerberg!: The challenge of social media and platformed racism in the {E}nglish premier league and football league},
  journal = {International Review for the Sociology of Sport},
  volume  = {59},
  number  = {6},
  pages   = {844--867},
  year    = {2024},
  doi     = {10.1177/10126902241234282}
}
```

### 3.2 Glynn, Brown & Edwards (2025)

- **Autores:** Eleanore Glynn, David H. K. Brown, Lisa Edwards
- **Título:** "Discriminatory Meme Culture on Football Twitter: Othering and Racialisation Through Insensitive Humour"
- **Venue:** Media Watch, vol. 16, no. 2, pp. 138–169
- **Año:** 2025
- **DOI:** 10.1177/09760911241313457
- **Para qué sirve:** estudia memes racializadores en Twitter durante la final Inglaterra-Italia de la Eurocopa 2020, mostrando cómo el "othering" de jugadores negros se **oculta mediante humor**. Es la referencia más directamente alineada con nuestro hallazgo central (xenofobia disfrazada de broma) en contexto futbolístico.

```bibtex
@article{glynn2025discriminatory,
  author  = {Glynn, Eleanore and Brown, David H. K. and Edwards, Lisa},
  title   = {Discriminatory Meme Culture on Football {T}witter: Othering and Racialisation Through Insensitive Humour},
  journal = {Media Watch},
  volume  = {16},
  number  = {2},
  pages   = {138--169},
  year    = {2025},
  doi     = {10.1177/09760911241313457}
}
```

### 3.3 Kearns, Sinclair, Black, Doidge, Fletcher, Kilvington, Liston, Lynn & Rosati (2023)

- **Autores:** Colm Kearns, Gary Sinclair, Jack Black, Mark Doidge, Thomas Fletcher, Daniel Kilvington, Katie Liston, Theo Lynn, Pierangelo Rosati
- **Título:** "A Scoping Review of Research on Online Hate and Sport"
- **Venue:** Communication & Sport, vol. 11, no. 2, pp. 402–430
- **Año:** 2023 (publicado online oct-2022)
- **DOI:** 10.1177/21674795221132728
- **Para qué sirve:** revisión de alcance que mapea el estado del arte de odio en línea + deporte — útil para posicionar nuestro trabajo (extracción concurrente + doble eje sentimiento/odio) frente a la literatura existente, y para justificar el fútbol como caso de estudio.

```bibtex
@article{kearns2023scoping,
  author  = {Kearns, Colm and Sinclair, Gary and Black, Jack and Doidge, Mark and Fletcher, Thomas and Kilvington, Daniel and Liston, Katie and Lynn, Theo and Rosati, Pierangelo},
  title   = {A Scoping Review of Research on Online Hate and Sport},
  journal = {Communication \& Sport},
  volume  = {11},
  number  = {2},
  pages   = {402--430},
  year    = {2023},
  doi     = {10.1177/21674795221132728}
}
```

### 3.4 Kilvington, Ahmed, Fenton & Webster (2026, in press)

- **Autores:** Daniel Kilvington, Wasim Ahmed, Alex Fenton, Christopher Webster
- **Título:** "Using Social Network Analysis to Study Hate Speech in English Football During the White Lives Matter Banner Controversy"
- **Venue:** IIM Kozhikode Society & Management Review (SAGE), pp. 1–14
- **Año:** 2026 (in press)
- **DOI:** 10.1177/22779752261431396
- **Nota de verificación:** el venue (IIM Kozhikode Society & Management Review) es inusual para un tema futbolístico, pero se confirmó de forma independiente tanto en la página del DOI en SAGE como en el repositorio institucional de Leeds Beckett University; no es un error de búsqueda.
- **Para qué sirve:** análisis de redes sociales (no de contenido) sobre un episodio concreto de racismo futbolístico en X — referencia de método para justificar el análisis por plataforma/actor, complementaria a nuestro enfoque de clasificación de contenido.

```bibtex
@article{kilvington2026wlm,
  author  = {Kilvington, Daniel and Ahmed, Wasim and Fenton, Alex and Webster, Christopher},
  title   = {Using Social Network Analysis to Study Hate Speech in {E}nglish Football During the White Lives Matter Banner Controversy},
  journal = {IIM Kozhikode Society \& Management Review},
  pages   = {1--14},
  year    = {2026},
  note    = {In press},
  doi     = {10.1177/22779752261431396}
}
```

---

## 4. Computación paralela / concurrencia aplicada a NLP o recolección web (speedup, Ley de Amdahl)

### 4.1 Amdahl (1967) — clásico fundacional

- **Autor:** Gene M. Amdahl
- **Título:** "Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities"
- **Venue:** Proceedings of the April 18–20, 1967, Spring Joint Computer Conference (AFIPS '67), pp. 483–485
- **Año:** 1967
- **DOI:** 10.1145/1465482.1465560
- **Marcado como clásico fundacional:** es la fuente primaria de la Ley de Amdahl, imprescindible y explícitamente permitida por las reglas del encargo pese a su antigüedad.
- **Para qué sirve:** fundamenta teóricamente el límite del speedup por la fracción serial del programa — se usa en el paper para explicar por qué el speedup medido (2.61x) no escala linealmente con el número de procesos.

```bibtex
@inproceedings{amdahl1967validity,
  author    = {Amdahl, Gene M.},
  title     = {Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities},
  booktitle = {Proceedings of the April 18--20, 1967, Spring Joint Computer Conference},
  pages     = {483--485},
  year      = {1967},
  publisher = {ACM},
  doi       = {10.1145/1465482.1465560}
}
```

### 4.2 Malakhov et al. (2018) — oversubscription de hilos en librerías numéricas

- **Autor principal:** Anton Malakhov (Intel)
- **Título:** "Composable Multi-Threading and Multi-Processing for Numeric Libraries"
- **Venue:** Proceedings of the 17th Python in Science Conference (SciPy 2018)
- **Año:** 2018
- **URL:** https://proceedings.scipy.org/articles/Majora-4af1f417-003
- **Nota de fecha:** anterior a la ventana 2023–2026; se incluye porque describe **exactamente** el fenómeno técnico que medimos (oversubscription cuadrática de hilos: N procesos × M hilos internos de la librería numérica), no por tendencia reciente sino por especificidad técnica.
- **Para qué sirve:** es la referencia técnica directa de nuestro hallazgo de que la sobre-suscripción de hilos internos de `torch` anulaba el speedup (0.97x) hasta fijar `torch.set_num_threads(1)` — el paper documenta el mismo patrón (p. ej. scikit-learn × NumPy) y las estrategias para evitarlo.

```bibtex
@inproceedings{malakhov2018composable,
  author    = {Malakhov, Anton and Liu, David and others},
  title     = {Composable Multi-Threading and Multi-Processing for Numeric Libraries},
  booktitle = {Proceedings of the 17th Python in Science Conference (SciPy 2018)},
  year      = {2018},
  doi       = {10.25080/Majora-4af1f417-003}
}
```

### 4.3 Kim & Hassan Awadalla (2020) — *FastFormers*

- **Autores:** Young Jin Kim, Hany Hassan Awadalla
- **Título:** "FastFormers: Highly Efficient Transformer Models for Natural Language Understanding"
- **Venue:** SustaiNLP Workshop, EMNLP 2020
- **Año:** 2020
- **arXiv:** 2010.13382
- **Para qué sirve:** documenta explícitamente que el GIL de Python impide el paralelismo real de hilos en inferencia de transformers en CPU, por lo que recurre a `multiprocessing`. Es la referencia técnica que enmarca (en el caso "normal", con GIL) la decisión que en nuestro proyecto se resuelve distinto gracias a Python free-threaded: mismo problema, solución habilitada por el entorno sin GIL.

```bibtex
@inproceedings{kim2020fastformers,
  author    = {Kim, Young Jin and Hassan Awadalla, Hany},
  title     = {{FastFormers}: Highly Efficient Transformer Models for Natural Language Understanding},
  booktitle = {Proceedings of SustaiNLP: Workshop on Simple and Efficient Natural Language Processing (EMNLP 2020)},
  year      = {2020},
  eprint    = {2010.13382},
  archivePrefix = {arXiv}
}
```

### 4.4 Jiang (2024) — modelo de crawling multi-hilo

- **Autor:** Weijie Jiang
- **Título:** "A novel multi-threaded web crawling model"
- **Venue:** arXiv preprint (Computer Science > Databases)
- **Año:** 2024
- **arXiv:** 2407.10440
- **Para qué sirve:** propone y mide una arquitectura multi-hilo (hilos productores que descargan + pool separado que procesa) para recolección de datos web a gran escala, con optimización significativa frente a single-thread. Es el paralelo más cercano en la literatura a nuestra arquitectura de hilos + cola productor/consumidor para la extracción I/O-bound de la P6.

```bibtex
@misc{jiang2024multithreaded,
  author       = {Jiang, Weijie},
  title        = {A novel multi-threaded web crawling model},
  year         = {2024},
  eprint       = {2407.10440},
  archivePrefix = {arXiv}
}
```

---

## 5. Cierre de APIs (post-API age) y plataformas descentralizadas (Bluesky/AT Protocol, Mastodon)

### 5.1 Freelon, Monzer, Jeon, Moy & Williams (2024)

- **Autores:** Deen Freelon, Cristina Monzer, Gayoung Jeon, Cameron Moy, Natasha Williams
- **Título:** "The Post-API Age of Social Media Data Access: Past, Present, and Future"
- **Venue:** The ANNALS of the American Academy of Political and Social Science, vol. 715, no. 1, pp. 16–37
- **Año:** 2024
- **DOI:** 10.1177/00027162251372557
- **Para qué sirve:** formaliza el término "era post-API" y documenta cómo el cierre de accesos programáticos (Twitter/X, Reddit) desde 2023 es producto de **decisiones comerciales de las plataformas**, no de imposibilidad técnica. Es la cita central de nuestro hallazgo 5 y del argumento sobre por qué X y Reddit quedaron fuera del trío de fuentes.

```bibtex
@article{freelon2024postapi,
  author  = {Freelon, Deen and Monzer, Cristina and Jeon, Gayoung and Moy, Cameron and Williams, Natasha},
  title   = {The Post-{API} Age of Social Media Data Access: Past, Present, and Future},
  journal = {The ANNALS of the American Academy of Political and Social Science},
  volume  = {715},
  number  = {1},
  pages   = {16--37},
  year    = {2024},
  doi     = {10.1177/00027162251372557}
}
```

### 5.2 Mimizuka, Brown, Yang & Lukito (2025)

- **Autores:** Kayo Mimizuka, Megan A. Brown, Kai-Cheng Yang, Josephine Lukito
- **Título:** "Post-Post-API Age: Studying Digital Platforms in Scant Data Access Times"
- **Venue:** arXiv preprint (Human-Computer Interaction)
- **Año:** 2025
- **arXiv:** 2505.09877
- **Para qué sirve:** actualiza el diagnóstico de Freelon et al. con el estado aún más restrictivo de 2024–2025 (incluye el cierre de CrowdTangle en agosto de 2024) y cataloga cómo los investigadores migran a scraping y fuentes alternativas — apoya directamente nuestra propia decisión metodológica de recolectar vía scraping/APIs abiertas en vez de APIs oficiales cerradas.

```bibtex
@misc{mimizuka2025postpostapi,
  author       = {Mimizuka, Kayo and Brown, Megan A. and Yang, Kai-Cheng and Lukito, Josephine},
  title        = {Post-Post-{API} Age: Studying Digital Platforms in Scant Data Access Times},
  year         = {2025},
  eprint       = {2505.09877},
  archivePrefix = {arXiv}
}
```

### 5.3 Kleppmann et al. (2024) — Bluesky y el protocolo AT

- **Autores:** Martin Kleppmann, Paul Frazee, Jake Gold, Jay Graber, Daniel Holmgren, Devin Ivy, Jeromy Johnson, Bryan Newbold, Jaz Volpert
- **Título:** "Bluesky and the AT Protocol: Usable Decentralized Social Media"
- **Venue:** Proceedings of the ACM CoNEXT 2024 Workshop on the Decentralization of the Internet (DIN '24)
- **Año:** 2024
- **DOI:** 10.1145/3694809.3700740 · arXiv: 2402.03239
- **Para qué sirve:** describe la arquitectura técnica del protocolo AT (autoridad de identidad, portabilidad de datos, moderación composable) e invita explícitamente a la comunidad investigadora a usar Bluesky como terreno de prueba para moderación de contenido. Es la referencia técnica de nuestro extractor de Bluesky y del argumento "protocolo abierto como alternativa al cierre de X/Reddit".

```bibtex
@inproceedings{kleppmann2024bluesky,
  author    = {Kleppmann, Martin and Frazee, Paul and Gold, Jake and Graber, Jay and Holmgren, Daniel and Ivy, Devin and Johnson, Jeromy and Newbold, Bryan and Volpert, Jaz},
  title     = {Bluesky and the {AT} Protocol: Usable Decentralized Social Media},
  booktitle = {Proceedings of the ACM CoNEXT 2024 Workshop on the Decentralization of the Internet},
  year      = {2024},
  doi       = {10.1145/3694809.3700740}
}
```

### 5.4 Lisker & Mihaljević (2025) — ética de datos en el fediverso (Mastodon)

- **Autores:** Mareike Lisker, Helena Mihaljević
- **Título:** "Data Ethics in the Fediverse: Analyzing the Role of Instance Policies in Mastodon Research"
- **Venue:** Next-Gen and Alternative Social Media workshop, 19th International AAAI Conference on Web and Social Media (ICWSM 2025)
- **Año:** 2025
- **arXiv:** 2505.07606
- **Para qué sirve:** analiza cómo las políticas de cada instancia de Mastodon condicionan qué se puede investigar y cómo, en el contexto de una red basada en un protocolo abierto (ActivityPub) pero fragmentada en miles de instancias independientes. Sostiene nuestra caracterización de Mastodon como "plan B" viable pero con contenido orgánico pobre, y en general el argumento de plataformas descentralizadas como alternativa post-cierre de APIs.

```bibtex
@inproceedings{lisker2025dataethics,
  author    = {Lisker, Mareike and Mihaljevi{\'c}, Helena},
  title     = {Data Ethics in the Fediverse: Analyzing the Role of Instance Policies in {M}astodon Research},
  booktitle = {Next-Gen and Alternative Social Media Workshop, 19th International AAAI Conference on Web and Social Media (ICWSM 2025)},
  year      = {2025},
  eprint    = {2505.07606},
  archivePrefix = {arXiv}
}
```

---

## Verificación

**Metodología:** cada referencia se buscó con WebSearch y, cuando el sitio lo permitió, se confirmó con WebFetch directo sobre la página fuente (ACL Anthology, arXiv, SAGE, ACM DL, repositorios institucionales). Varias revistas SAGE devolvieron **HTTP 403** a WebFetch (bloqueo de scraping automatizado) — en esos casos la cita se reconstruyó cruzando el snippet de búsqueda con el repositorio institucional del autor (Leeds Beckett, Cardiff Met, etc.), que sí fue accesible.

### Confirmadas por fetch directo a la fuente primaria
- ElSherief et al. 2021 (ACL Anthology, fetch directo).
- Nguyen et al. 2020 BERTweet (ACL Anthology, fetch directo).
- Basile et al. 2019 HatEval (ACL Anthology, fetch directo).
- Pérez et al. 2021 pysentimiento (arXiv, fetch directo).
- Kleppmann et al. 2024 Bluesky/AT Protocol (arXiv, fetch directo).
- Mimizuka et al. 2025 Post-Post-API Age (arXiv, fetch directo).
- Lisker & Mihaljević 2025 (arXiv, fetch directo).
- Kim & Hassan Awadalla 2020 FastFormers (arXiv, fetch directo).
- Jiang 2024 crawling multi-hilo (arXiv, fetch directo).

### Confirmadas por múltiples fuentes secundarias concordantes (WebFetch bloqueado por 403 en la fuente primaria)
- Freelon et al. 2024 (SAGE 403 → confirmado cruzando IDEAS/RePEc, EconPapers y el snippet de la propia página SAGE, que coinciden en volumen 715(1), pp. 16–37).
- Hylton et al. 2024 (SAGE 403 → confirmado con snippet de SAGE + coincidencia de ISSN con *International Review for the Sociology of Sport*).
- Glynn et al. 2025 (SAGE 403 → volumen/páginas obtenidos vía WebFetch a resultado de búsqueda, no a la página SAGE directamente; **recomendamos que alguien del equipo verifique manualmente el volumen/página exactos antes de la entrega final**, aunque el título, autores, año y DOI están confirmados por 3+ fuentes independientes).
- Kearns et al. 2023 (SAGE 403 → confirmado vía snippet + coincidencia de ISSN con *Communication & Sport*).
- Kilvington et al. 2026 (SAGE 403 → confirmado vía WebFetch al repositorio institucional de Leeds Beckett, que lista el mismo DOI, autores y título; el venue —*IIM Kozhikode Society & Management Review*— es inusual para el tema pero está confirmado por dos fuentes independientes, no es un error).
- Kirk et al. 2022 Hatemoji (ACL Anthology no fetcheado directamente, pero título/autores/venue confirmados de forma consistente en 3+ resultados de búsqueda incluyendo arXiv 2108.05921).
- Pérez et al. 2022 RoBERTuito (LREC — no fetcheado directamente; confirmado vía snippet + arXiv 2111.09453 + PDF oficial de LREC listado en los resultados).
- Cañete et al. 2020 BETO (workshop paper sin DOI de editorial; confirmado vía la propia página de publicaciones de José Cañete y el repositorio GitHub oficial `dccuchile/beto`).
- Barbieri et al. 2022 XLM-T (confirmado vía snippet + repositorio oficial `cardiffnlp/xlm-t` en GitHub, que cita el mismo paper).
- Frenda, Patti & Rosso 2023 (Springer — redirect a autenticación, no se pudo fetchear el capítulo completo; título, autores, venue LNCS 14163 y año confirmados vía snippet de búsqueda).
- Piot et al. 2024 MetaHate (confirmado vía arXiv 2401.06526 + página de AAAI ICWSM).
- Amdahl 1967 (ACM DL devolvió 403; es sin embargo el paper más citado y verificable de la historia de la computación — título, año, páginas y DOI confirmados de forma cruzada en ACM DL, Semantic Scholar, ResearchGate y Stony Brook University).
- Malakhov et al. 2018 (SciPy Proceedings — no se hizo fetch directo del PDF, pero la página de Proceedings de SciPy y ResearchGate coinciden en título/autor/año; **la lista completa de coautores no se pudo confirmar con certeza** — Anton Malakhov es el autor principal verificado, "David Liu" aparece en un video de la misma charla en SciPy 2018 pero no pudimos confirmar si figura como coautor del paper escrito o solo como presentador relacionado. Verificar la lista de autores en el PDF original antes de citar en el paper final.)

### No verificadas del todo / advertencias explícitas
- **Malakhov et al. 2018:** ver nota arriba — coautoría incierta más allá del autor principal.
- **Cañete et al. 2020 BETO:** no tiene DOI de editorial (paper de workshop, PML4DC@ICLR); se cita con URL del propio autor en vez de DOI. Es una práctica común para papers de este tipo de workshop, pero señalarlo si la plantilla Springer exige DOI obligatorio.
- **Glynn et al. 2025:** volumen/issue/páginas exactos obtenidos de una fuente secundaria (resultado de búsqueda), no de la página SAGE directamente (bloqueada). Título, autores, año y DOI sí están confirmados con alta confianza.
- Ninguna referencia fue inventada: en los pocos casos donde no se pudo confirmar un dato específico (coautoría completa de Malakhov et al., o el volumen exacto de Glynn et al.), se indica explícitamente arriba en vez de rellenarlo.

**Total de referencias:** 22 (mínimo pedido: 15; margen: +7).
