
## Objetivos 

No âmbito da Unidade Curricular de **Algoritmos e Técnicas de Programação**, foi desenvolvida uma aplicação em Python destinada à gestão hospitalar. O sistema permite gerir informação relativa aos doentes, recorrendo a estruturas de dados complexas (listas e dicionários), garantindo a correta organização, manipulação e apresentação dos dados ao utilizador.

Adicionalmente, o projeto integra um módulo de **simulação do serviço de urgências**, possibilitando a análise do comportamento das filas de espera e da ocupação dos médicos em função de diferentes parâmetros. Os resultados são apresentados através de **gráficos estatísticos**, facilitando a avaliação do desempenho do serviço. Para melhorar a interação com o utilizador, foi ainda desenvolvida uma **interface gráfica intuitiva**, recorrendo às bibliotecas *FreeSimpleGUI*, *matplotlib*, *datetime* e *json*.

## Descrição do Problema

O problema consiste na simulação do funcionamento de uma clínica médica, com o objetivo de modelar o atendimento de doentes ao longo do tempo. Os doentes chegam à clínica de forma aleatória, são atendidos por um número limitado de médicos e, na ausência de disponibilidade imediata, aguardam em fila de espera.

A chegada dos doentes é modelada por uma distribuição de Poisson e a duração das consultas segue distribuições estatísticas pré-definidas. Durante a simulação são recolhidas métricas de desempenho, como tempos de espera, tamanho das filas e ocupação dos médicos.

Os resultados obtidos são analisados e representados graficamente, permitindo avaliar o impacto de diferentes parâmetros no desempenho global da clínica e compreender o seu comportamento em diversos cenários.

## Dataset Utilizado

O dataset utilizado corresponde ao ficheiro **pessoas.json**, armazenado em formato JSON. A sua estrutura consiste numa lista de dicionários, onde cada dicionário representa um indivíduo com os respetivos atributos demográficos e clínicos relevantes para a simulação.

Esta organização permite um acesso simples e flexível à informação, facilitando a integração dos dados no modelo de simulação e o seu tratamento ao longo da execução do sistema. De seguida, apresenta-se um excerto ilustrativo de um dos registos do dataset, com alguns campos omitidos para simplificação.

## Componentes Principais da Simulação

A gestão da fila de eventos é assegurada pelas funções `enqueue` e `dequeue`, que permitem inserir e remover eventos de forma ordenada pelo instante temporal, garantindo o correto processamento cronológico da simulação. A função `procuraPosQueue` apoia este mecanismo, determinando a posição adequada para a inserção de novos eventos.

A geração dos recursos humanos é realizada através das funções `gera_medicos` e `gera_enfermeiros`, responsáveis pela criação das equipas disponíveis na simulação. Os médicos são distribuídos por especialidade de acordo com pesos definidos, enquanto os enfermeiros são utilizados no processo de triagem como recursos limitados.

A função `gera_especialidade_prevista` permite atribuir previamente uma especialidade clínica ao doente com base em características simples, como a idade, contribuindo para um maior realismo do modelo.

A seleção do próximo doente a ser atendido é efetuada pela função `prox_doente`, que respeita os níveis de prioridade clínica, assegurando que os casos mais urgentes são tratados em primeiro lugar.

O núcleo da simulação é implementado na função `simula_eventos`, onde são gerados e processados todos os eventos relevantes, sendo também recolhidas métricas de desempenho para posterior análise estatística e representação gráfica.

Por fim, a função `verifica_obito` modela a possibilidade de ocorrência de óbito com base em fatores clínicos do doente, acrescentando uma dimensão adicional de realismo à simulação.

## Conceção e Proposta de Resolução

A aplicação desenvolvida recorre à biblioteca **PySimpleGUI** para a implementação da interface gráfica, com o objetivo de proporcionar uma utilização simples e intuitiva na gestão da informação hospitalar. A **interface principal** disponibiliza acesso às funcionalidades essenciais da aplicação, incluindo o carregamento e armazenamento da base de dados, a inserção de novos doentes, a atualização do estado dos registos e a consulta da informação existente.




O **carregamento da base de dados** é realizado através da seleção de um ficheiro no formato JSON, permitindo ao utilizador iniciar a aplicação com os dados pretendidos de forma rápida e eficiente.




Para a **inserção de novos doentes**, foi desenvolvida uma janela dedicada, composta por campos de texto e listas de seleção, assegurando um processo simples, controlado e consistente.


Adicionalmente, a aplicação permite a visualização e edição da **ficha individual do doente**, onde se encontra informação detalhada, como dados pessoais, especialidade atribuída e estado do doente, possibilitando uma gestão mais completa e organizada dos registos.



## Relatórios
A página de Relatórios foi concebida para permitir a realização de simulações e a
visualização de resultados gráficos associados ao funcionamento do sistema hospitalar.
Nesta interface, o utilizador pode definir um conjunto de parâmetros relevantes, como
a taxa de chegada de doentes, o número de médicos disponíveis e a capacidade da sala
de espera, ajustando assim o comportamento da simulação.

## Conclusão

O sistema desenvolvido possibilita a leitura e interpretação de uma base de dados
composta por estruturas de dados complexas, nomeadamente listas e dicionários, repre-
sentando um conjunto de pessoas e respetivos atributos. A aplicação permite percorrer
essa informação, organizar os dados e apresentá-los de forma estruturada ao utilizador,
garantindo uma correta manipulação e acesso à informação.

