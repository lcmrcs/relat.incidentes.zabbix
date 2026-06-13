from pathlib import Path
import textwrap


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
PDF_PATH = REPORTS_DIR / "documentacao_projeto_zabbix.pdf"

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 48
MARGIN_TOP = 54
MARGIN_BOTTOM = 52


DOCUMENT = [
    ("title", "Documentacao do Projeto - Relatorio de Incidente Zabbix"),
    (
        "body",
        "Este documento explica a funcao dos arquivos e dos blocos principais "
        "do projeto. A ideia e servir como guia de estudo e manutencao: voce "
        "consegue entender o que cada parte faz, por que ela existe e onde ela "
        "entra no fluxo do relatorio.",
    ),
    ("heading", "1. Visao geral do projeto"),
    (
        "body",
        "O projeto consulta a API do Zabbix, coleta eventos de problema, "
        "classifica cada host por unidade e tipo de equipamento, gera "
        "indicadores e exporta os resultados em Excel, HTML e PDF.",
    ),
    (
        "body",
        "O fluxo principal e: carregar configuracao, definir periodo, consultar "
        "o Zabbix, enriquecer os dados com hosts e tags, classificar os "
        "incidentes, montar os resumos e gerar os arquivos finais.",
    ),
    ("heading", "2. Estrutura de arquivos"),
    (
        "bullet",
        "README.md: apresenta o objetivo do projeto, requisitos, instalacao e "
        "uso basico.",
    ),
    (
        "bullet",
        "COMANDOS.md: guia rapido para executar comandos no terminal, ativar a "
        "venv, gerar relatorios e usar Git.",
    ),
    (
        "bullet",
        "zabbix-report/test_zabbix_api.py: teste de conexao com a API do "
        "Zabbix antes de gerar relatorios.",
    ),
    (
        "bullet",
        "zabbix-report/zabbix_report.py: script principal, responsavel por "
        "buscar, organizar e exportar os incidentes.",
    ),
    (
        "bullet",
        "zabbix-report/templates/report_template.html: modelo visual usado para "
        "renderizar o relatorio HTML interativo.",
    ),
    (
        "bullet",
        "zabbix-report/requirements.txt: dependencias Python necessarias para o "
        "projeto funcionar.",
    ),
    (
        "bullet",
        "zabbix-report/reports/: pasta onde ficam os arquivos gerados: HTML, "
        "PDF, Excel e esta documentacao.",
    ),
    ("heading", "3. Blocos do test_zabbix_api.py"),
    (
        "body",
        "Este arquivo existe para responder uma pergunta simples antes de rodar "
        "o relatorio completo: o Python consegue acessar o Zabbix usando a URL "
        "e o token configurados?",
    ),
    (
        "bullet",
        "Importacoes: carrega os modulos os, requests e dotenv. Eles permitem "
        "ler variaveis de ambiente, enviar HTTP e carregar o arquivo .env.",
    ),
    (
        "bullet",
        "Carregar .env: usa load_dotenv para disponibilizar ZABBIX_URL e "
        "ZABBIX_TOKEN no Python sem colocar credenciais dentro do codigo.",
    ),
    (
        "bullet",
        "Validar variaveis: para a execucao cedo caso URL ou token estejam "
        "ausentes. Isso evita uma chamada errada para a API.",
    ),
    (
        "bullet",
        "Headers HTTP: define Content-Type como application/json, necessario "
        "porque o Zabbix usa JSON-RPC.",
    ),
    (
        "bullet",
        "Payload de teste: monta uma chamada host.get leve, suficiente para "
        "confirmar autenticacao e conexao.",
    ),
    (
        "bullet",
        "Requisicao HTTP: envia o POST para a API com timeout, evitando que o "
        "terminal fique preso indefinidamente.",
    ),
    (
        "bullet",
        "Validacao da resposta: confere status HTTP, converte JSON e verifica "
        "se a API retornou erro JSON-RPC.",
    ),
    (
        "bullet",
        "Exibir resultado: mostra alguns hosts retornados para confirmar que "
        "o acesso ao Zabbix esta funcional.",
    ),
    ("heading", "4. Blocos iniciais do zabbix_report.py"),
    (
        "bullet",
        "Importacoes: reune bibliotecas para terminal, datas, HTTP, planilhas, "
        "HTML, .env, contadores e escrita de arquivos.",
    ),
    (
        "bullet",
        "Constante REQUEST_TIMEOUT: limita o tempo das chamadas HTTP para que "
        "uma falha de rede nao trave o script.",
    ),
    (
        "bullet",
        "Caminhos do projeto: BASE_DIR, ENV_PATH, TEMPLATES_DIR e REPORTS_DIR "
        "garantem que o script encontre os arquivos certos mesmo executado de "
        "outra pasta.",
    ),
    (
        "bullet",
        "Argumentos do terminal: argparse permite escolher periodo, data "
        "inicial e status sem editar o codigo.",
    ),
    (
        "bullet",
        "parse_period: converte valores como 24h, 2d, 5d, 7d e historico para "
        "o formato usado no calculo de datas.",
    ),
    (
        "bullet",
        "Carregar .env: busca ZABBIX_URL e ZABBIX_TOKEN de forma segura, fora "
        "do Git.",
    ),
    (
        "bullet",
        "Definir periodo: calcula time_from e time_till em timestamp UNIX, que "
        "e o formato esperado pela API do Zabbix.",
    ),
    ("heading", "5. Bloco de comunicacao com a API"),
    (
        "bullet",
        "Headers: informa que o corpo da requisicao sera JSON.",
    ),
    (
        "bullet",
        "call_zabbix_api: funcao central para enviar chamadas ao Zabbix, tratar "
        "timeout, conexao, JSON invalido e erros retornados pela API.",
    ),
    (
        "bullet",
        "Payload principal: usa problem.get quando o relatorio pede apenas "
        "incidentes abertos, pois e mais leve para o historico aberto.",
    ),
    (
        "bullet",
        "event.get: usado quando tambem e necessario considerar eventos "
        "resolvidos, porque ele permite consultar ocorrencias no periodo.",
    ),
    (
        "bullet",
        "time_from opcional: no modo historico completo, o script nao envia data "
        "inicial e deixa o Zabbix retornar desde o registro mais antigo.",
    ),
    ("heading", "6. Bloco de hosts, triggers e recuperacao"),
    (
        "bullet",
        "r_eventid: identifica evento de recuperacao, usado para descobrir se "
        "um incidente foi resolvido e quando.",
    ),
    (
        "bullet",
        "trigger.get: cada problema aponta para uma trigger. Essa consulta "
        "descobre em qual host a trigger esta.",
    ),
    (
        "bullet",
        "Dicionarios auxiliares: host_by_trigger, host_details_by_id e "
        "resolved_at_by_event aceleram o cruzamento dos dados.",
    ),
    (
        "bullet",
        "Catalogo de unidades: host.get com tags monta a relacao codigo -> nome "
        "da unidade usando a etiqueta unidade do Zabbix.",
    ),
    ("heading", "7. Blocos de classificacao"),
    (
        "bullet",
        "severity_map: traduz os numeros do Zabbix para nomes claros: "
        "Informacao, Atencao, Media, Alta e Desastre.",
    ),
    (
        "bullet",
        "equipment_order: define a ordem visual do filtro de equipamento no "
        "HTML.",
    ),
    (
        "bullet",
        "classify_equipment: le o nome do host e classifica como Mikrotik, "
        "Switch, NVR, Central de Alarme, Terminal Facial, Portal Detector de "
        "Metal, Camera, Servidor Zabbix, Servidor ou Diversos.",
    ),
    (
        "bullet",
        "extract_school_unit: tenta extrair codigo e nome da unidade a partir "
        "do nome do host quando a tag nao e suficiente.",
    ),
    (
        "bullet",
        "extract_unit_code: pega apenas o codigo numerico inicial do host, "
        "quando existir.",
    ),
    (
        "bullet",
        "classify_unit_group: separa escola, Servidor Zabbix e CONFEA VPN. "
        "Assim Zabbix e VMs da CONFEA nao entram no painel das unidades.",
    ),
    (
        "bullet",
        "get_unit_tag_value: le a etiqueta unidade diretamente das tags do "
        "host no Zabbix.",
    ),
    (
        "bullet",
        "clean_unit_name e score_unit_name_candidate: escolhem o melhor nome "
        "para cada unidade quando ha mais de um host candidato.",
    ),
    (
        "bullet",
        "build_unit_catalog: cria o catalogo final de unidades escolares usado "
        "durante a montagem do relatorio.",
    ),
    ("heading", "8. Bloco de resumo e indicadores"),
    (
        "bullet",
        "build_report_summary: calcula totais, abertos, resolvidos, incidentes "
        "unicos, repeticoes, severidade, equipamento, unidade e hosts mais "
        "afetados.",
    ),
    (
        "bullet",
        "incident_key: agrupa repeticoes do mesmo problema no mesmo host para "
        "diferenciar evento do Zabbix e incidente unico.",
    ),
    (
        "bullet",
        "format_counter: transforma contadores em listas com total e percentual, "
        "facilitando o uso no HTML e no PDF.",
    ),
    ("heading", "9. Bloco de geracao de PDF interno do relatorio"),
    (
        "bullet",
        "pdf_escape: prepara textos para nao quebrar a sintaxe interna do PDF.",
    ),
    (
        "bullet",
        "wrap_text: quebra textos longos em linhas menores.",
    ),
    (
        "bullet",
        "add_pdf_text: adiciona texto em uma pagina PDF usando coordenadas.",
    ),
    (
        "bullet",
        "build_summary_pdf_page: monta a primeira pagina do PDF com indicadores "
        "executivos.",
    ),
    (
        "bullet",
        "build_pdf_page: monta paginas de detalhamento com os incidentes.",
    ),
    (
        "bullet",
        "write_pdf_report: junta as paginas e grava o arquivo PDF final sem "
        "depender de biblioteca externa.",
    ),
    ("heading", "10. Bloco de lista de incidentes"),
    (
        "body",
        "Depois de obter problemas, hosts e tags, o script percorre cada item "
        "retornado pelo Zabbix e transforma os dados brutos em linhas legiveis.",
    ),
    (
        "bullet",
        "Data e status: converte timestamp para data humana e define Aberto ou "
        "Resolvido.",
    ),
    (
        "bullet",
        "Filtros de status: respeita --status abertos, resolvidos ou todos.",
    ),
    (
        "bullet",
        "Classificacao: aplica equipamento, unidade e agrupamento especial.",
    ),
    (
        "bullet",
        "Dicionario do incidente: cada linha guarda host, unidade, equipamento, "
        "incidente, severidade, status, datas e eventid.",
    ),
    ("heading", "11. Bloco de exportacao"),
    (
        "bullet",
        "DataFrame pandas: transforma a lista de dicionarios em tabela para "
        "facilitar a exportacao Excel.",
    ),
    (
        "bullet",
        "main_incidents: contem apenas as unidades escolares, excluindo Zabbix "
        "e CONFEA VPN.",
    ),
    (
        "bullet",
        "zabbix_incidents: guarda apenas incidentes do Servidor Zabbix.",
    ),
    (
        "bullet",
        "confea_incidents: guarda apenas as VMs da CONFEA monitoradas pela VPN.",
    ),
    (
        "bullet",
        "Excel: cria abas Unidades, Servidor Zabbix, CONFEA VPN e Todos.",
    ),
    (
        "bullet",
        "HTML: usa Jinja2 para preencher o template report_template.html com "
        "dados e indicadores.",
    ),
    (
        "bullet",
        "PDF: gera uma versao estatica para envio ou arquivamento.",
    ),
    (
        "bullet",
        "Resumo final no terminal: mostra os caminhos dos arquivos gerados e "
        "os totais principais.",
    ),
    ("heading", "12. Blocos do report_template.html"),
    (
        "bullet",
        "CSS visual: define cores, cards, tabelas, botoes, filtros, modal e "
        "responsividade.",
    ),
    (
        "bullet",
        "Cabecalho: mostra titulo, data de geracao e periodo consultado.",
    ),
    (
        "bullet",
        "Resumo: apresenta eventos, incidentes unicos, abertos, resolvidos e "
        "severidades.",
    ),
    (
        "bullet",
        "Indicadores: mostra listas de severidade, equipamento, host e unidade "
        "mais afetada.",
    ),
    (
        "bullet",
        "Paineis especiais: Servidor Zabbix aparece em vermelho e CONFEA VPN em "
        "painel separado.",
    ),
    (
        "bullet",
        "Filtros interativos: permitem filtrar por situacao, unidade escolar e "
        "equipamento sem recarregar a pagina.",
    ),
    (
        "bullet",
        "Busca de unidade: reduz a lista visualmente enquanto o usuario digita "
        "codigo ou nome.",
    ),
    (
        "bullet",
        "Tabela principal: exibe apenas incidentes de unidade escolar.",
    ),
    (
        "bullet",
        "Janelas de detalhe: botoes abrem dialogs com informacoes completas de "
        "cada incidente ou grupo especial.",
    ),
    (
        "bullet",
        "JavaScript: atualiza contadores, aplica filtros, abre janelas e evita "
        "que opcoes desaparecam quando o filtro atual nao tem resultados.",
    ),
    ("heading", "13. Comandos principais"),
    (
        "bullet",
        "Ativar ambiente: source zabbix-report/venv/bin/activate.",
    ),
    (
        "bullet",
        "Testar API: python zabbix-report/test_zabbix_api.py.",
    ),
    (
        "bullet",
        "Relatorio padrao: python zabbix-report/zabbix_report.py.",
    ),
    (
        "bullet",
        "Ultimas 24h: python zabbix-report/zabbix_report.py --periodo 24h.",
    ),
    (
        "bullet",
        "Historico aberto: python zabbix-report/zabbix_report.py --periodo "
        "historico --status abertos.",
    ),
    (
        "bullet",
        "Desde uma data: python zabbix-report/zabbix_report.py --desde "
        "2026-01-01.",
    ),
    ("heading", "14. Observacoes importantes"),
    (
        "bullet",
        "O arquivo .env nunca deve ir para o Git, pois guarda URL e token.",
    ),
    (
        "bullet",
        "O relatorio historico pode demorar mais porque consulta muitos dados.",
    ),
    (
        "bullet",
        "As categorias especiais Zabbix e CONFEA VPN sao separadas para manter "
        "os indicadores das unidades escolares limpos.",
    ),
    (
        "bullet",
        "A aba Todos do Excel preserva a visao completa, enquanto as abas "
        "separadas organizam melhor a analise.",
    ),
]


def pdf_escape(text):
    """Escapa caracteres especiais usados pela sintaxe de texto do PDF."""

    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def add_wrapped(lines, kind, text):
    """Quebra um paragrafo em linhas visuais apropriadas para a pagina."""

    widths = {
        "title": 54,
        "heading": 68,
        "body": 88,
        "bullet": 84,
    }
    prefix = "- " if kind == "bullet" else ""
    subsequent = "  " if kind == "bullet" else ""

    wrapped = textwrap.wrap(
        text,
        width=widths[kind],
        initial_indent=prefix,
        subsequent_indent=subsequent,
        break_long_words=False,
    )

    if not wrapped:
        wrapped = [""]

    for line in wrapped:
        lines.append((kind, line))

    lines.append(("space", ""))


def build_lines():
    """Transforma a estrutura DOCUMENT em linhas paginaveis."""

    lines = []

    for kind, text in DOCUMENT:
        add_wrapped(lines, kind, text)

    return lines


def paginate(lines):
    """Divide o conteudo em paginas respeitando margens e altura da pagina."""

    pages = []
    current = []
    y = PAGE_HEIGHT - MARGIN_TOP

    metrics = {
        "title": (18, 24),
        "heading": (13, 19),
        "body": (10, 14),
        "bullet": (10, 14),
        "space": (10, 7),
    }

    for kind, text in lines:
        _, height = metrics[kind]

        if y - height < MARGIN_BOTTOM and current:
            pages.append(current)
            current = []
            y = PAGE_HEIGHT - MARGIN_TOP

        current.append((kind, text, y))
        y -= height

    if current:
        pages.append(current)

    return pages


def build_page_stream(page_lines, page_number, total_pages):
    """Monta o fluxo de comandos PDF de uma pagina."""

    commands = [
        "BT /F1 8 Tf 48 28 Td "
        f"({pdf_escape(f'Pagina {page_number} de {total_pages}')}) Tj ET"
    ]

    for kind, text, y in page_lines:
        if kind == "space":
            continue

        size = {
            "title": 18,
            "heading": 13,
            "body": 10,
            "bullet": 10,
        }[kind]
        x = MARGIN_X

        commands.append(
            f"BT /F1 {size} Tf {x} {y} Td ({pdf_escape(text)}) Tj ET"
        )

    return "\n".join(commands)


def write_pdf(path, pages):
    """Escreve um PDF simples usando apenas a biblioteca padrao do Python."""

    objects = []
    total_pages = len(pages)
    page_object_numbers = []

    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append("PAGES_PLACEHOLDER")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for index, page_lines in enumerate(pages, start=1):
        stream = build_page_stream(page_lines, index, total_pages)
        stream_bytes = stream.encode("latin-1", errors="replace")
        content_number = len(objects) + 2
        page_number = len(objects) + 1
        page_object_numbers.append(page_number)
        objects.append(
            "<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            "/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {content_number} 0 R >>"
        )
        objects.append(
            f"<< /Length {len(stream_bytes)} >>\nstream\n"
            f"{stream}\nendstream"
        )

    kids = " ".join(f"{number} 0 R" for number in page_object_numbers)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {total_pages} >>"

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")
    offsets = [0]

    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("latin-1"))
        pdf.extend(obj.encode("latin-1", errors="replace"))
        pdf.extend(b"\nendobj\n")

    xref_at = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_at}\n"
            "%%EOF\n"
        ).encode("latin-1")
    )

    path.write_bytes(pdf)


def main():
    """Gera o PDF de documentacao dentro da pasta reports."""

    REPORTS_DIR.mkdir(exist_ok=True)
    pages = paginate(build_lines())
    write_pdf(PDF_PATH, pages)
    print(f"PDF de documentacao gerado: {PDF_PATH}")


if __name__ == "__main__":
    main()
