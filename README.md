# 🎧 PDF para Audiobook (MP3)

Aplicação em Python que recebe um livro em formato **PDF (de até 200 MB)** e o transforma em um **audiobook narrado em formato MP3** com voz masculina em português brasileiro.

> O sistema lê exclusivamente o conteúdo escrito no PDF — sem resumir e sem inventar informações — e salva o progresso automaticamente no computador para não perder o trabalho caso o PC seja desligado durante a conversão.

---

## ⚙️ Como o projeto funciona

### 1. Leitura e limpeza do PDF (`PyMuPDF`)
* Extrai o texto de todas as páginas do livro mantendo a ordem original de leitura.
* Reconstrói títulos em letras maiúsculas que possuem espaçamento largo na diagramação (ex.: transforma `P R Ó L O G O` em `Prólogo.`).
* Une linhas que pertencem à mesma frase para que preposições (`o`, `se`, `em`, `de`, `na`, `te`) sejam lidas de forma contínua, sem pausas robóticas no fim de cada linha.
* Expande abreviações comuns (`cap.`, `pág.`, `p. ex.`, `sr.`, `dr.`, `obs.`, `nº`, `etc.`) para evitar que o narrador corte a frase no meio ou tente ler a abreviação em outro idioma.
* Ignora números de página isolados, cabeçalhos e rodapés que se repetem nas margens das páginas.

### 2. Divisão do texto e Narração
* Divide o livro em trechos menores respeitando o fim das frases e parágrafos.
* Permite escolher entre 4 opções de motor de voz na tela:
  * **Edge TTS (Gratuito):** usa a voz masculina nativa em português da Microsoft sem precisar de chave de API.
  * **Google Gemini TTS:** usa as vozes masculinas da Google (`Charon`, `Orus`, `Puck`, `Fenrir`) mediante chave de API do Google AI Studio.
  * **OpenAI TTS:** usa as vozes masculinas da OpenAI (`onyx`, `ash`, `echo`) mediante chave de API da OpenAI.
  * **ElevenLabs:** usa as vozes da sua conta ElevenLabs mediante chave de API.

### 3. Backup automático em disco
* Cria automaticamente a pasta `projetos_audiobook/` no mesmo local do código.
* Cada trecho de áudio gerado (`chunk_00000.mp3`, `chunk_00001.mp3`...) é salvo imediatamente no disco.
* Se o computador desligar antes de terminar o livro, ao abrir o programa novamente o projeto salvo aparece no topo da tela e continua exatamente do trecho em que parou.
* Ao final, o `FFmpeg` (já incluído via biblioteca Python) junta todos os trechos em um único arquivo `.mp3` pronto para ouvir e baixar.

---

## 📂 Estrutura de arquivos

```text
├── app.py                  # Código principal da aplicação e interface web
├── requirements.txt        # Bibliotecas necessárias para rodar o projeto
├── README.md               # Documentação do projeto
└── projetos_audiobook/     # Pasta criada automaticamente para salvar o progresso e os arquivos MP3
```

---

## 📋 O que é necessário para rodar

* Ter o **Python** (versão 3.9 ou superior) instalado no computador.
* Ter **conexão com a internet** (pois as vozes são geradas pelos servidores de síntese de voz).
* Um arquivo de livro em **PDF de até 200 MB** que possua texto selecionável (não apenas fotos escaneadas).

---

## 🚀 Passo a passo para executar o projeto

### Passo 1: Baixar os arquivos
Coloque os arquivos `app.py` e `requirements.txt` dentro de uma mesma pasta no seu computador.

### Passo 2: Instalar as bibliotecas necessárias
Abra o terminal (Prompt de Comando ou PowerShell) dentro dessa pasta e execute:

```bash
pip install -r requirements.txt
```

Isso instalará automaticamente as 6 bibliotecas utilizadas pelo projeto:
* `streamlit` — cria a tela no navegador
* `pymupdf` — lê o arquivo PDF
* `edge-tts` — gera a voz gratuita da Microsoft
* `requests` — conecta às APIs opcionais Gemini, OpenAI e ElevenLabs
* `imageio-ffmpeg` — junta os pedaços de áudio no MP3 final
* `wordfreq` — ajuda a identificar palavras da língua portuguesa em títulos estilizados

### Passo 3: Iniciar a aplicação
Ainda no terminal, execute o comando abaixo:

```bash
streamlit run app.py
```

O navegador abrirá automaticamente no endereço `http://localhost:8501`.

---

## 🖥️ Como usar na tela

1. Clique no botão **"Upload"** e selecione o arquivo `.pdf` do livro (máximo de 200 MB).
2. Aguarde alguns segundos até aparecer a contagem de páginas, o total de caracteres e a prévia do texto extraído.
3. Escolha o **Motor de narração** desejado:
   * Para usar gratuitamente sem chave, mantenha selecionado **Edge TTS**.
   * Para usar **Google Gemini**, **OpenAI** ou **ElevenLabs**, selecione a opção correspondente e cole a sua chave de API.
4. Clique em **"🔊 Testar Voz neste Livro (Amostra)"** para ouvir um trecho curto dos primeiros parágrafos e conferir se gostou da voz e do ritmo.
5. Clique em **"🎧 Gerar / Continuar Audiobook (.mp3)"** para iniciar a conversão do livro inteiro.
6. Quando a barra chegar a 100% (ou se quiser baixar o que já foi convertido usando o botão de MP3 Parcial), clique em **"⬇️ Baixar Audiobook Completo (.mp3)"**.