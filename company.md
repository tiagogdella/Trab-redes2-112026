Regras que valem para todas as organizações
Os nomes das máquinas e das redes são exatamente os descritos aqui. Endereços, regras de filtragem, limites dos alertas e intervalos de coleta são decisões do grupo.
Além das máquinas listadas, toda organização tem a rede gerencia e o gerente, que fica só nessa rede. A coluna "Rede de gerência" indica quais outras máquinas também estão nela.
Na política de acesso, "Internet" é a rede internet. Cada sonda pode acessar o mesmo que os usuários da rede em que ela está. Pacotes ICMP, como os do ping e do traceroute, passam entre as redes da organização, exceto a de gerência, e delas para a Internet; vindos da Internet, só entram os que respondem a esse tráfego. Todo tráfego que a política não lista é descartado.
As condições dos enlaces são simuladas com netem. "Em cada sentido" significa netem nas duas pontas do enlace; "na saída de X para Y" significa netem só na interface de X que está na rede Y.
Algumas interfaces e máquinas só entram em uso na mudança. Uma interface nessa situação começa sem endereço IP: o script de inicialização da máquina remove o endereço que o Docker atribui. Uma máquina nessa situação começa com endereço, mas sem o serviço. Um roteador nessa situação já começa com o agente SNMP e com a filtragem, que descarta todo o tráfego que o atravessa até a mudança.

8. Espaço Ponto Comum
Espaço de trabalho compartilhado (coworking) em dois andares, alugado a três empresas, chamadas de inquilinas: Alfa e Beta no primeiro andar, Gama no segundo. Cada inquilina tem a própria rede, e nenhuma pode alcançar a outra. Todas usam o portal de reserva de salas e o servidor de arquivos do espaço, e o portal também atende o público pela Internet.

Máquina	Redes	Função	Rede de gerência
rt-borda	internet, comum, enlace-andar1, enlace-andar2	Roteador de borda	Sim
rt-andar1	enlace-andar1, alfa, beta	Roteador do primeiro andar	Sim
rt-andar2	enlace-andar2, gama	Roteador do segundo andar	Sim
srv-portal	comum	Portal de reserva de salas: nginx, 80/tcp	Sim
srv-arquivos	comum	Arquivos compartilhados, simulados por um nginx em 8080/tcp	Sim
srv-dns	comum	Nomes	Sim
cli-alfa	alfa	Computador da Alfa	Não
cli-beta	beta	Computador da Beta	Não
cli-gama	gama	Computador da Gama	Não
externo	internet	Público que reserva salas	Não
sonda-internet	internet	Sonda	Sim
sonda-gama	gama	Sonda	Sim
Condições dos enlaces. enlace-andar1 e enlace-andar2: 5 ms de atraso em cada sentido e taxa de 20 Mbit/s.

Critérios de sucesso.

 	Critério
C1	http://srv-portal/ responde com o código 200 a sonda-internet
C2	http://srv-portal/ responde com o código 200 a sonda-gama em menos de 50 ms
C3	http://srv-arquivos:8080/ responde com o código 200 a sonda-gama
Política de acesso.

De	Para	Tráfego permitido
Internet	srv-portal	80/tcp
alfa, beta, gama	srv-portal	80/tcp
alfa, beta, gama	srv-arquivos	8080/tcp
alfa, beta, gama	srv-dns	53/udp e 53/tcp
alfa, beta, gama	Internet	Todo
Alfa e Beta estão no mesmo roteador: o isolamento entre elas também é feito em rt-andar1.

Falhas a provocar. Falha do serviço: encerrar o nginx de srv-portal. Falha do enlace: enlace-andar2.

Mudança: trocar o endereçamento da rede gama. A Gama pediu outro prefixo para a sua rede, porque o atual coincide com o de outra rede que ela usa. A rede gama passa a usar um novo prefixo, escolhido pelo grupo dentro de 10.0.0.0/8 e sem sobreposição com os demais. Mudam os endereços de rt-andar2, cli-gama e sonda-gama nessa rede, as rotas dos roteadores, as regras de filtragem e as entradas em srv-dns. A rede Docker gama continua a mesma: o prefixo novo é configurado dentro das máquinas. Validação: o prefixo antigo não aparece em nenhuma rota, regra ou entrada de nome; gama continua sem alcançar alfa e beta; e C1 a C3 continuam cumpridos.