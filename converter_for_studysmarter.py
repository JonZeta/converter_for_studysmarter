"""
DESCRIPCIÓN:
Este script de Python permite procesar archivos PDF que contengan preguntas y respuestas y convertirlos en archivos de Excel he importarlos como flashcards en https://www.studysmarter.es/. Para asegurar una correcta conversión es necesario seguir ciertos requisitos:

REQUISITOS:

Reemplazar todas las comillas dobles por otro carácter similar, como por ejemplo “. Esto es necesario porque para guardar líneas múltiples, Excel utiliza las comillas dobles para diferenciar el contenido de una celda.

Asegurarse de que todas las preguntas tengan el siguiente formato:
QUESTION NO: XXX
XXXXXXX
XXXXXXXXX
A. XXX
B. XXX
C. XXX
D. XXX
Answer: X X

Pueden haber hasta 6 alternativas, es decir, hasta la letra F.

En las respuestas, cada letra de respuesta correcta debe ir separada por espacios.
"""

import re
import argparse
from pypdf import PdfReader
from sys import exit

# Crear objeto ArgumentParser
parser = argparse.ArgumentParser(description='Procesar archivo PDF de preguntas y respuestas')

# Agregar argumento para archivo PDF
parser.add_argument('--pdf', metavar='FILE', type=str, required=True, help='Nombre del archivo PDF a procesar')

# Agregar argumento opcional verbose
parser.add_argument('--verbose', action='store_true', help='Activar salida detallada')

# Obtener argumentos de la línea de comandos
args = parser.parse_args()

# Abrir el archivo PDF en modo de lectura binaria
reader = PdfReader(args.pdf)
texto_completo = ""
for page in reader.pages:
    texto_completo += page.extract_text() + "\n"
#print(texto_completo)
texto_completo = texto_completo.replace("\"","''")

#Borrar todo el texto que haya antes de la primera pregunta, si no hay texto borrará la primera pregunta.
patron = re.compile(r'(?s).+?(?=\nQUESTION NO:)',flags=re.MULTILINE)
match = patron.search(texto_completo)
if match:
    texto_completo = texto_completo[match.end()+1:]

#Borrar el texto de fin de página.
texto_completo = re.sub(r'(?s)(?=IT Certification Guaranteed, The Easy Way!)(.*?)(\d+)', r"",texto_completo,flags=re.MULTILINE)

# Dividimos el texto en las distintas preguntas
preguntas = texto_completo.split('QUESTION')

for i, pregunta in enumerate(preguntas[1:], start=1):

    # Si existe una explicación de momento la quitamos.
    #TODO: añadir el texto del bloque de explicación a la columna explicación en el csv.
    if 'Explanation' in pregunta:
        match = re.search(r'(?s).*(?=\nExplanation)', pregunta, flags=re.DOTALL)
        if match:
                pregunta = match.group()

    # Busco las respuestas TRUE y añado formato para el CSV:
    m = re.search(r"Answer: .?([A-Z])(?: .?([A-Z]))?(?: .?([A-Z]))?(?: .?([A-Z]))?",pregunta)
    respuestas_correctas = m.groups()
    g = bool(m)
    if g == True:
        for letra in m.groups():
            if letra == None:
                break
            m = re.search(fr"(?:^|\n){letra}\.(.*?)(?=\n[A-Z]|\Z)",pregunta, flags=re.DOTALL)
            pos = m.end()
            pregunta_a_lista=list(pregunta)
            pregunta_a_lista.insert(pos,'"\tTRUE')
            pregunta=''.join(pregunta_a_lista)

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
            pregunta_a_lista=list(pregunta)
            pregunta_a_lista.insert(pos,'"\tFALSE')
            pregunta=''.join(pregunta_a_lista)
        pregunta = re.sub(fr'(?:^|\n)({letra_respuesta}\.)',r'\t"\1', pregunta, flags=re.DOTALL)

    #Añado una tabulacion y unas dobles comillas antes de la respuesta A para formato del CSV
    m = re.search(r".*?(?=\bA\.)",pregunta)
    g = bool(m)
    if g == True:
        pos = m.end()
        pregunta_a_lista=list(pregunta)
        pregunta_a_lista.insert(pos,'\t"')
        pregunta=''.join(pregunta_a_lista) 

    # Unimos 'QUESTION' con la pregunta modificada, además le añado dobles comillas y un salto de linea siempre que no sea el primer question
    preguntas[i] = '\"QUESTION' + pregunta
    
    # Unimos las preguntas de nuevo en un solo string
    texto_modificado = ''.join(preguntas)

    #Escribimos el csv, para posterior importarlo en https://www.studysmarter.es/
    with open('resultado.csv', 'w') as res:
        res.write(texto_modificado)
        porcentaje = int((i/len(preguntas)) * 100)
        print(f"Completado: {porcentaje}%", end="\r")
#Finalmente añado la cabecera al csv y la escribimos en el fichero
texto_modificado = "Question\tAnswer A\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer B\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer C\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer D\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer E\tanswer is correct (TRUE if yes, FALSE if no)\tAnswer F\tanswer is correct (TRUE if yes, FALSE if no)\tTags\tHints\tExplanation\n{}".format(texto_modificado)
with open('resultado.csv', 'w') as res:
        res.write(texto_modificado)
        porcentaje = int((i/len(preguntas)) * 100)
        print(f"Completado: {porcentaje}%", end="\r")
