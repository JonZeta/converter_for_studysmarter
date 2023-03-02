import re
import textwrap
from pypdf import PdfReader
from sys import exit
from argparse import ArgumentParser, HelpFormatter

# Crear objeto ArgumentParser

class RawFormatter(HelpFormatter):
    def _fill_text(self, text, width, indent):
        return "\n".join([textwrap.fill(line, width) for line in textwrap.indent(textwrap.dedent(text), indent).splitlines()])

program_descripton = f'''
    DESCRIPCIÓN:
    Este script de Python permite procesar archivos PDF que contengan preguntas y respuestas y convertirlos en archivos de Excel he importarlos como flashcards en https://www.studysmarter.es/. Para asegurar una correcta conversión es necesario seguir ciertos requisitos:

    REQUISITOS:
    1.- Se reemplazaran todas las comillas dobles por dos comillas simples. Esto es necesario porque para guardar líneas múltiples en el csv, Excel utiliza las comillas dobles para diferenciar el contenido de una celda.

    2.- Asegurarse de que todas las preguntas tengan el siguiente formato:
    
    QUESTION NO: ???????????????
    ????????????????????????????
    ????????????????????????????
    A. ???????
    B. ???????
    C. ???????
    D. ???????
    Answer: ? ?
    Explanation: ???????????????
    ????????????????????????????
    ????????????????????????????

    3.- Si se indica el parametro --pdf se crea un archivo de texto extraido del pdf indicado, luego hay que abrirlo con algun pragrama como notepad++ y asegurarse de adaptarlo a como se indica en la plantilla
    Principalmente hay que asegurarse de que los elementos empiecen al comienzo de la linea y el texo despues de la ultima pregunta del documento.
    También borrar textos de cambio de página, para ello se puede usar una expresion regular en notepad++ si es necesario.

    4.- Pueden haber hasta 6 alternativas, es decir, hasta la letra F.

    5.- En las respuestas, cada letra de respuesta correcta debe ir separada por espacios.

    7.- Luego de realizar los ajustes manuales ejecutar el script con el parametro --txt y generará un archivo .csv que luego hay que abrir con Excel o similar y seleccionar tabulacion como separador, finalmente guardarlo en formato xlsx.
    
    8.- Una vez guardado en formato xlsx ya se puede importar en https://www.studysmarter.es/

    Author: https://github.com/JonZeta/converter_for_studysmarter
    '''

parser = ArgumentParser(description=program_descripton, formatter_class=RawFormatter)

# Agregar argumento opcional para archivo PDF
parser.add_argument('--pdf', metavar='FILE', type=str, help='Nombre del archivo PDF a procesar')

# Agregar argumento opcional para archivo TXT
parser.add_argument('--txt', metavar='FILE', type=str, help='Nombre del archivo TXT a procesar')

# Obtener argumentos de la línea de comandos
args = parser.parse_args()

# Verificar que se haya especificado exactamente uno de los argumentos
if args.pdf is None and args.txt is None:
    print("Debe especificar uno de los argumentos --pdf o --txt")
    exit(1)
elif args.pdf is not None and args.txt is not None:
    print("Debe especificar solamente uno de los argumentos --pdf o --txt")
    exit(1)

# Procesar archivo PDF
if args.pdf is not None:
    if not args.pdf.endswith('.pdf'):
        print("El archivo indicado en el argumento --pdf debe tener la extensión .pdf")
        exit(1)
    reader = PdfReader(args.pdf)
    texto_completo = ""
    for i,page in enumerate(reader.pages):
        texto_completo += page.extract_text() + "\n"
        porcentaje = int((i/len(reader.pages)) * 100)
        print(f"Completado: {porcentaje}%", end="\r")
        archivo = args.pdf[:-4]+'.txt'
    with open(archivo, 'w') as res:
        res.write(texto_completo)
        print("\nSe he creado el archivo "+archivo)
        
# Procesar archivo TXT
if args.txt is not None:
    if not args.txt.endswith('.txt'):
        print("El archivo indicado en el argumento --txt debe tener la extensión .txt")
        exit(1)
    with open(args.txt, 'r') as f:
        texto_completo = f.read()

    #Limpiamos el texto y cambiamos todas las dobles comillas por 2 comillas simples para poder guardar texto multilinea entre comillas en el csv
    texto_completo = texto_completo.replace("\"","''")

    #Limpiamos tabulaciones preexistentes
    texto_completo = texto_completo.replace("\t","")

    #Borrar todo el texto que haya antes de la primera pregunta, si no hay texto borrará la primera pregunta.
    patron = re.compile(r'(?s).+?(?=\nQUESTION NO:)',flags=re.MULTILINE)
    match = patron.search(texto_completo)
    if match:
        texto_completo = texto_completo[match.end()+1:]

    # Dividimos el texto en las distintas preguntas
    preguntas = texto_completo.split('QUESTION NO')

    for i, pregunta in enumerate(preguntas[1:], start=1):
        
        # Buscamos si hay explicación si la hay la guardamos en la variable explanation y luego borramos el texto la explicación barra procesar el resto del texto, añadiremos la explicación nuevamente mas tarde
        explanation = ''
        if 'Explanation' in pregunta:
            match = re.search(r'(?s)(?=Explanation).*', pregunta, flags=re.DOTALL)
            if bool(match):
                explanation = match.group()
            match = re.search(r'(?s).*(?=\nExplanation)', pregunta, flags=re.DOTALL)
            if bool(match):
                pregunta = match.group()

        # Busco las respuestas TRUE y y las guardo en un array
        m = re.search(r"Answer: .?([A-Z])(?: .?([A-Z]))?(?: .?([A-Z]))?(?: .?([A-Z]))?",pregunta)
        respuestas_correctas = m.groups()

        #Quitamos la linea Answer: con las respuestas, ya que ahora las respuestas estan indicadas en las columnas con el valor TRUE 
        pregunta = re.sub(r"(?<=\n)Answer:.+?(\n|$)",r"",pregunta)

        #Buscamos cuantas alternativas tiene la pregunta
        respuestas = re.findall(r"(?<=\n)([A-G])\.",pregunta)

        #Parseamos las alternativas, y las formateamos para el CSV, además indicamos cuales son las alternativas FALSE
        for j, respuesta in enumerate(respuestas):
            letra_respuesta = respuestas[j]
            if letra_respuesta not in respuestas_correctas:
                if j < len(respuestas)-1:
                    m = re.search(fr'(?s)(\n{letra_respuesta}\.).*(?=\n{respuestas[j+1]}.)',pregunta, flags=re.DOTALL)
                else:
                    m = re.search(fr'(?s)(\n{letra_respuesta}\.).*(?=\n)',pregunta, flags=re.DOTALL)
                pos = m.end()
                alternativa_a_lista=list(pregunta)
                alternativa_a_lista.insert(pos,'"\tFALSE')
                pregunta=''.join(alternativa_a_lista)
            elif letra_respuesta in respuestas_correctas:
                if j < len(respuestas)-1:
                    m = re.search(fr'(?s)(\n{letra_respuesta}\.).*(?=\n{respuestas[j+1]}.)',pregunta, flags=re.DOTALL)
                else:
                    m = re.search(fr'(?s)(\n{letra_respuesta}\.).*(?=\n)',pregunta, flags=re.DOTALL)
                pos = m.end()
                alternativa_a_lista=list(pregunta)
                alternativa_a_lista.insert(pos,'"\tTRUE')
                pregunta=''.join(alternativa_a_lista)
            pregunta = re.sub(fr'(?:^|\n)({letra_respuesta}\.)',r'\t"\1', pregunta, flags=re.DOTALL)
            
            # Añadimos explicación, 16 columnas tiene la plantilla de studysmarter, menos x alternativas tiene la pregunta por 2 ya que cada alternativa tiene su valor (TRUE o FALSE) mas la pregunta
            if j == len(respuestas)-1:
                if explanation:
                    patron = fr'(?:^|\t"){letra_respuesta}..*(\w)'
                    posicion = re.search(patron, pregunta, re.DOTALL).end()
                    pregunta = pregunta[:posicion]
                    tabs = 16 - (len(respuestas) * 2 + 1) # El + 2 es por la tabulacion añadida en la linea anterior y por la primera que hay entre la pregunta y la primera alternativa
                    tabs_str = '\t' * tabs
                    pregunta = pregunta + tabs_str + '\"' + explanation + '\"' + '\n'

        #Añado unas dobles comillas antes de la alternativa A para envolver el enunciado de la pregunta formato del CSV
        m = re.search(r".*?(?=\t)",pregunta)
        g = bool(m)
        if g == True:
            pos = m.end()
            alternativa_a_lista=list(pregunta)
            alternativa_a_lista.insert(pos,'\"')
            pregunta=''.join(alternativa_a_lista)

        

        # Esto elimina la letra de las alternativas A. B. etc, dado que en studysmarter automaticamente se añade la letra a la alternativa correspondiente.
        l=0
        while l < len(respuestas):
            pregunta= pregunta.replace('\"'+respuestas[l]+'.',"\"")
            l+=1

        # Unimos 'QUESTION' con la pregunta modificada, además le añado dobles comillas y un salto de linea siempre que no sea el primer question
        preguntas[i] = '\"QUESTION NO' + pregunta

        # Unimos las preguntas de nuevo en un solo string
        texto_modificado = ''.join(preguntas)

        # Escribimos el csv, para posterior importarlo en https://www.studysmarter.es/
        archivo = args.txt[:-4]+'.csv'
        with open(archivo, 'w') as res:
            res.write(texto_modificado)
            porcentaje = int((i/len(preguntas)) * 100)
            print(f"Completado: {porcentaje}%", end="\r")

    #Finalmente añado la cabecera al csv y la escribimos en el fichero
    texto_modificado = "Question\tAnswer A\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer B\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer C\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer D\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer E\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer F\tanswer is correct (TRUE if yes, FALSE if no)\tTags\tHints\tExplanation\n{}".format(texto_modificado)
    archivo = args.txt[:-4]+'.csv'
    with open(archivo, 'w') as res:
            res.write(texto_modificado)
            porcentaje = int((i/len(preguntas)) * 100)
            print(f"Completado: {porcentaje}%", end="\r")
