import csv
from flask import Flask, render_template, request, redirect, url_for, session
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import time
from openpyxl import Workbook
from datetime import datetime
import pandas as pd
from flask import send_file
from zipfile import ZipFile  # Adicionando importação para a classe ZipFile
from io import BytesIO
from flask import make_response




app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

def verificar_credenciais(usuario, senha):
    caminho_csv = os.path.join('dados', 'usuarios.csv')
    with open(caminho_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['usuario'] == usuario and row['senha'] == senha:
                return row['role']  # Retorna o papel do usuário se as credenciais forem encontradas
    return None  # Retorna None se as credenciais não forem encontradas

@app.route('/login', methods=['GET', 'POST'])
def realizar_login():
    erro = None
    if request.method == 'POST':
        usuario = request.form['username']
        senha = request.form['password']
        role = verificar_credenciais(usuario, senha)
        if role:
            session['usuario'] = usuario
            session['role'] = role
            criar_arquivo_csv(usuario, role)  # Criar arquivo CSV para o usuário, se não existir
            return redirect(url_for('dashboard'))
        else:
            erro = 'Usuário ou senha incorretos!'
    return render_template('login.html', erro=erro)

def criar_arquivo_csv(usuario, role):
    if role == 'funcionario':
        caminho_csv = os.path.join('funcionarios', f'{usuario}.csv')
    elif role == 'admin':
        caminho_csv = os.path.join('administradores', f'{usuario}.csv')
    else:
        print(f"Papel de usuário inválido: {role}")
        return
    
    if not os.path.isfile(caminho_csv):
        with open(caminho_csv, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['data', 'hora_inicio', 'hora_pausa', 'hora_recomeco', 'hora_fim', 'folga', 'placa'])  # Escrever cabeçalho CSV, se necessário

def salvar_registro_csv(usuario, dados):
    caminho_csv = os.path.join('funcionarios', f'{usuario}.csv')
    try:
        with open(caminho_csv, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            registros = list(reader)
    except FileNotFoundError:
        registros = []

    data_atual = dados[0]

    # Verificar se já existe um registro para a data atual
    registro_existente = next((registro for registro in registros if registro['data'] == data_atual), None)

    if registro_existente:
        # Atualizar o registro existente com as novas informações
        for key, value in zip(registro_existente.keys(), dados):
            registro_existente[key] = value
    else:
        # Criar um novo registro
        novo_registro = {'data': data_atual}
        for key, value in zip(['hora_inicio', 'hora_pausa', 'hora_recomeco', 'hora_fim', 'folga', 'placa'], dados[1:]):
            novo_registro[key] = value
        registros.append(novo_registro)

    # Escrever os registros de volta no arquivo CSV
    try:
        with open(caminho_csv, 'w', newline='') as csvfile:
            fieldnames = ['data', 'hora_inicio', 'hora_pausa', 'hora_recomeco', 'hora_fim', 'folga', 'placa']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(registros)
        print(f"Dados salvos com sucesso para o usuário {usuario}: {dados}")
        return True
    except Exception as e:
        print(f"Erro ao salvar registro CSV para o usuário {usuario}: {e}")
        return False


def obter_nome_funcionario(usuario):
    caminho_csv = os.path.join('dados', 'usuarios.csv')
    
    # Verificar se o arquivo CSV existe
    if not os.path.isfile(caminho_csv):
        print(f"Erro: Arquivo CSV não encontrado em {caminho_csv}")
        return 'Erro: Arquivo CSV não encontrado'

    try:
        with open(caminho_csv, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['usuario'] == usuario:
                    return row['nome']  # Retorna o nome do funcionário se o usuário for encontrado
        return 'Usuário Desconhecido'  # Retorna uma string padrão se o usuário não for encontrado
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV: {e}")
        return 'Erro ao ler o arquivo CSV'

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'usuario' in session:
        usuario = session['usuario']
        nome_funcionario = obter_nome_funcionario(usuario)
        role = session['role']
        horas_preenchidas = ler_hora_prenchida()  # Ler os dados do arquivo CSV do usuário logado
        mensagem = None
        
        if request.method == 'POST':
            if role == 'funcionario':
                data_atual = adicionar_data_registro()
                hora_inicio = request.form['hora_inicio']
                hora_pausa = request.form['hora_pausa']
                hora_recomeco = request.form['hora_recomeco']
                hora_fim = request.form['hora_fim']
                folga = request.form.get('folga', False)  # Se a folga não estiver marcada, será False
                placa = request.form['placa_veiculo']
                dados = [data_atual, hora_inicio, hora_pausa, hora_recomeco, hora_fim, folga, placa]
                if salvar_registro_csv(usuario, dados):
                    mensagem = 'Registro de horário salvo com sucesso!'
                    # Após salvar o registro, redireciona para o dashboard
                    return redirect(url_for('dashboard'))
                else:
                    mensagem = 'Erro ao salvar registro de horário. Por favor, tente novamente.'
        
        elif role == 'admin':
            # Verificar se há funcionários sem registros para o dia atual
            funcionarios_sem_registro = verificar_registros_faltantes()
            print("Funcionários sem registro:", funcionarios_sem_registro)  # Adicionando um print para depuração
            return render_template('admin_dashboard.html', nome_funcionario=nome_funcionario, role=role, funcionarios_sem_registro=funcionarios_sem_registro)
        
        elif role == 'funcionario':
            return render_template('funcionario_dashboard.html', nome_funcionario=nome_funcionario, role=role, sucesso=mensagem, horas_prenchidas=horas_preenchidas)
    
    return redirect(url_for('login'))




@app.route('/usuarios')
def usuarios():
    if 'usuario' in session and session['role'] == 'admin':
        # Ler os dados dos usuários do arquivo CSV
        usuarios = ler_dados_usuarios()
        return render_template('usuarios.html', usuarios=usuarios)
    else:
        return redirect(url_for('login'))

def ler_dados_usuarios():
    dados_usuarios = []
    caminho_csv = 'dados/usuarios.csv'
    try:
        with open(caminho_csv, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                dados_usuarios.append(row)
    except FileNotFoundError:
        print(f'Arquivo {caminho_csv} não encontrado.')
    return dados_usuarios

@app.route('/adicionar_usuario', methods=['POST'])
def adicionar_usuario():
    if 'usuario' in session and session['role'] == 'admin':
        novo_usuario = {
            'usuario': request.form['usuario'],
            'senha': request.form['senha'],
            'nome': request.form['nome'],
            'role': request.form['role']
        }
        adicionar_usuario_csv(novo_usuario)
        return redirect(url_for('usuarios'))
    else:
        return redirect(url_for('login'))

def adicionar_usuario_csv(novo_usuario):
    caminho_csv = 'dados/usuarios.csv'
    try:
        with open(caminho_csv, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['usuario', 'senha', 'nome', 'role']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(novo_usuario)
    except FileNotFoundError:
        print(f'Arquivo {caminho_csv} não encontrado.')

@app.route('/editar_usuario/<usuario>', methods=['GET', 'POST'])
def editar_usuario(usuario):
    if 'usuario' in session and session['role'] == 'admin':
        if request.method == 'GET':
            usuario_editar = ler_usuario_por_usuario(usuario)
            if usuario_editar:
                return render_template('editar_usuario.html', usuario=usuario_editar)
            else:
                return 'Usuário não encontrado', 404
        elif request.method == 'POST':
            dados_atualizados = {
                'usuario': request.form['usuario'],
                'senha': request.form['senha'],
                'nome': request.form['nome'],
                'role': request.form['role']
            }
            atualizar_usuario_csv(usuario, dados_atualizados)
            return redirect(url_for('usuarios'))
    else:
        return redirect(url_for('login'))

def ler_usuario_por_usuario(usuario):
    caminho_csv = 'dados/usuarios.csv'
    try:
        with open(caminho_csv, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['usuario'] == usuario:
                    return row
    except FileNotFoundError:
        print(f'Arquivo {caminho_csv} não encontrado.')

def atualizar_usuario_csv(usuario, dados_atualizados):
    caminho_csv = 'dados/usuarios.csv'
    try:
        with open(caminho_csv, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            linhas = list(reader)
        with open(caminho_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['usuario', 'senha', 'nome', 'role']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for linha in linhas:
                if linha['usuario'] == usuario:
                    linha.update(dados_atualizados)
                writer.writerow(linha)
    except FileNotFoundError:
        print(f'Arquivo {caminho_csv} não encontrado.')





@app.route('/excluir_usuario/<usuario>', methods=['POST'])
def excluir_usuario(usuario):
    if 'usuario' in session and session['role'] == 'admin':
        excluir_usuario_csv(usuario)
        excluir_arquivo_usuario(usuario)  # Chama a função para excluir o arquivo do usuário
        return redirect(url_for('usuarios'))
    else:
        return redirect(url_for('login'))

def excluir_usuario_csv(usuario):
    caminho_csv = 'dados/usuarios.csv'
    try:
        with open(caminho_csv, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            linhas = list(reader)
        with open(caminho_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['usuario', 'senha', 'nome', 'role']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for linha in linhas:
                if linha['usuario'] != usuario:
                    writer.writerow(linha)
    except FileNotFoundError:
        print(f'Arquivo {caminho_csv} não encontrado.')

def excluir_arquivo_usuario(usuario):
    caminho_arquivo = os.path.join('funcionarios', f'{usuario}.csv')
    try:
        os.remove(caminho_arquivo)
        print(f'Arquivo {caminho_arquivo} excluído com sucesso.')
    except FileNotFoundError:
        print(f'Arquivo {caminho_arquivo} não encontrado.')





@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('role', None)
    return redirect(url_for('login'))

def adicionar_data_registro():
    # Obtém a data atual
    data_atual = datetime.now().strftime('%Y-%m-%d')
    return data_atual


#GRAFICOS FUNCIONARIO#
# Função para ler os dados do arquivo CSV de um funcionário
def ler_dados_funcionario(caminho_arquivo):
    with open(caminho_arquivo, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        return list(reader)

# Função para processar os dados de todos os funcionários
def processar_dados_funcionarios(pasta_funcionarios):
    dados_consolidados = []
    for pasta, _, arquivos in os.walk(pasta_funcionarios):
        for arquivo in arquivos:
            if arquivo.endswith('.csv'):
                caminho_arquivo = os.path.join(pasta, arquivo)
                dados_funcionario = ler_dados_funcionario(caminho_arquivo)
                dados_consolidados.extend(dados_funcionario)
    return dados_consolidados

# Função para gerar o gráfico consolidado
def gerar_grafico_consolidado(dados_consolidados):
    horas_inicio = [float(funcionario['hora_inicio'].split(':')[0]) if funcionario['hora_inicio'] else None for funcionario in dados_consolidados]
    horas_pausa = [float(funcionario['hora_pausa'].split(':')[0]) if funcionario['hora_pausa'] else None for funcionario in dados_consolidados]
    horas_recomeco = [float(funcionario['hora_recomeco'].split(':')[0]) if funcionario['hora_recomeco'] else None for funcionario in dados_consolidados]
    horas_fim = [float(funcionario['hora_fim'].split(':')[0]) if funcionario['hora_fim'] else None for funcionario in dados_consolidados]

    plt.figure(figsize=(10, 6))
    plt.plot(horas_inicio, label='Hora de Início', marker='o')
    plt.plot(horas_pausa, label='Hora de Pausa', marker='o')
    plt.plot(horas_recomeco, label='Hora de Recomeço', marker='o')
    plt.plot(horas_fim, label='Hora de Fim', marker='o')
    plt.xlabel('Funcionários')
    plt.ylabel('Horas')
    plt.title('Horas de Trabalho dos Funcionários Consolidadas')
    plt.legend()
    plt.grid(True)
    plt.savefig('static/img/grafico-consolidado.png')  # Salva o gráfico consolidado como uma imagem

# Pasta onde estão os arquivos CSV dos funcionários
pasta_funcionarios = 'funcionarios'

# Processar os dados de todos os funcionários
dados_consolidados = processar_dados_funcionarios(pasta_funcionarios)

# Gerar o gráfico consolidado
gerar_grafico_consolidado(dados_consolidados)
#


#looping que executa a cada 10 minutos para atualizar o grafico
def main():
    while True:
        # Processar os dados de todos os funcionários
        dados_consolidados = processar_dados_funcionarios(pasta_funcionarios)
        
        # Gerar o gráfico consolidado
        gerar_grafico_consolidado(dados_consolidados)
        print("Gráfico consolidado atualizado com sucesso.")

        # Pausa a execução por 10 minutos
        time.sleep(600)  # 600 segundos = 10 minutos

#GRAFICO ACABA AQUI

#funcionarios que nao prencheram hora no dia
# Função para verificar se um funcionário registrou horas para o dia atual
# Função para verificar se um funcionário registrou horas para o dia atual
def verificar_registros_faltantes():
    print("Verificando registros faltantes")
    funcionarios_sem_registro = []
    pasta_funcionarios = 'funcionarios'

    # Obter a data atual
    data_atual = datetime.now().strftime('%Y-%m-%d')

    # Listar todos os arquivos na pasta funcionarios
    arquivos = os.listdir(pasta_funcionarios)

    # Percorrer cada arquivo na pasta funcionarios
    for arquivo in arquivos:
        if arquivo.endswith('.csv'):
            caminho_arquivo = os.path.join(pasta_funcionarios, arquivo)
            with open(caminho_arquivo, 'r', newline='') as file:
                reader = csv.DictReader(file)
                if any(linha['data'] == data_atual for linha in reader):
                    continue  # Se encontrar algum registro para a data atual, continue para o próximo arquivo
                else:
                    funcionario = os.path.splitext(arquivo)[0]
                    funcionarios_sem_registro.append(funcionario)

    print("Funcionários sem registro:", funcionarios_sem_registro)  # Para depuração
    return funcionarios_sem_registro
#######################################################################################################
# Função para ler os dados do arquivo CSV do usuário logado
def ler_hora_prenchida():
    dados_usuario = {}
    data_atual = datetime.now().strftime('%Y-%m-%d')
    if 'usuario' in session:
        usuario = session['usuario']
        nome_arquivo = f'{usuario}.csv'
        caminho_arquivo = f'funcionarios/{nome_arquivo}'  # caminho para os arquivos do usuário
        # Verifica se o arquivo CSV do usuário existe
        if os.path.exists(caminho_arquivo):
            with open(caminho_arquivo, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['data'] == data_atual:
                        # Verifica se os campos de hora estão vazios e, se estiverem, atribui None
                        dados_usuario['hora_inicio'] = row.get('hora_inicio')
                        dados_usuario['hora_pausa'] = row.get('hora_pausa')
                        dados_usuario['hora_recomeco'] = row.get('hora_recomeco')
                        dados_usuario['hora_fim'] = row.get('hora_fim')
                        break
    return dados_usuario


##########################
#####tela funcionarios
# Função para obter os nomes dos funcionários
# Função para obter os nomes dos funcionários
def obter_nomes():
    funcionarios = []
    try:
        pasta_funcionarios = 'funcionarios'
        for arquivo in os.listdir(pasta_funcionarios):
            if arquivo.endswith('.csv'):
                funcionarios.append(os.path.splitext(arquivo)[0])
    except FileNotFoundError:
        print('Pasta de funcionários não encontrada.')
    return funcionarios

# Função para obter os dados do funcionário dentro do intervalo de datas especificado
def obter_dados(funcionario, data_inicio, data_fim):
    dados = []
    try:
        caminho_arquivo = f'funcionarios/{funcionario}.csv'
        if os.path.exists(caminho_arquivo):
            df = pd.read_csv(caminho_arquivo)
            # Verificando se o arquivo CSV contém a coluna 'data'
            if 'data' in df.columns:
                # Convertendo a coluna 'data' para o formato desejado
                df['data'] = pd.to_datetime(df['data'], format='%Y-%m-%d').dt.date
                # Filtrando os dados pelo intervalo de datas
                dados = df[(df['data'] >= data_inicio) & (df['data'] <= data_fim)].to_dict(orient='records')
    except FileNotFoundError:
        print(f'Arquivo CSV do funcionário {funcionario} não encontrado.')
    return dados


# Rota para a página de funcionários
@app.route('/funcionarios', methods=['GET', 'POST'])
def funcionarios():
    if 'usuario' in session and session['role'] == 'admin':
        if request.method == 'POST':
            data_inicio = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date()
            data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date()
            funcionarios = obter_nomes()
            arquivo_zip = gerar_arquivos_excel(funcionarios, data_inicio, data_fim)
            if arquivo_zip:
                return arquivo_zip
            else:
                return 'Erro ao gerar arquivos Excel', 500
        else:
            funcionarios = obter_nomes()
            return render_template('funcionarios.html', funcionarios=funcionarios)
    else:
        return redirect(url_for('login'))


# Função para gerar os arquivos Excel para os funcionários dentro do intervalo de datas especificado
# Função para gerar os arquivos Excel para os funcionários dentro do intervalo de datas especificado
'''
def gerar_arquivos_excel(funcionarios, data_inicio, data_fim):
    try:
        for funcionario in funcionarios:
            dados_funcionario = obter_dados(funcionario, data_inicio, data_fim)
            if dados_funcionario:
                # Aqui você pode usar as datas de início e fim conforme necessário
                # Por exemplo, você pode convertê-las em strings no formato desejado para incluir no nome do arquivo
                data_inicio_str = data_inicio.strftime('%d-%m-%Y')
                data_fim_str = data_fim.strftime('%d-%m-%Y')
                nome_arquivo = f'export/{funcionario}_{data_inicio_str}_{data_fim_str}.xlsx'

                df = pd.DataFrame(dados_funcionario)
                df.to_excel(nome_arquivo, index=False)
                print(f"Arquivo Excel gerado com sucesso para o funcionário {funcionario} dentro do intervalo de datas especificado.")
            else:
                print(f"Não há dados disponíveis para o funcionário {funcionario} dentro do intervalo de datas especificado.")
    except Exception as e:
        print(f'Erro ao gerar arquivos Excel: {e}')
'''

def gerar_arquivos_excel(funcionarios, data_inicio, data_fim):
    try:
        dados_disponiveis = False  # Flag para verificar se há dados disponíveis para pelo menos um funcionário

        with BytesIO() as buffer_zip:
            with ZipFile(buffer_zip, 'w') as arquivo_zip:
                for funcionario in funcionarios:
                    dados_funcionario = obter_dados(funcionario, data_inicio, data_fim)
                    if dados_funcionario:
                        # Aqui você pode usar as datas de início e fim conforme necessário
                        # Por exemplo, você pode convertê-las em strings no formato desejado para incluir no nome do arquivo
                        data_inicio_str = data_inicio.strftime('%d-%m-%Y')
                        data_fim_str = data_fim.strftime('%d-%m-%Y')
                        nome_arquivo = f'{funcionario}_{data_inicio_str}_{data_fim_str}.xlsx'

                        df = pd.DataFrame(dados_funcionario)
                        buffer = BytesIO()  # Crie um buffer BytesIO para armazenar o arquivo Excel
                        df.to_excel(buffer, index=False)  # Salve o DataFrame no buffer BytesIO
                        buffer.seek(0)  # Volte para o início do buffer

                        # Adicione o conteúdo do arquivo ao arquivo zip com o nome desejado
                        arquivo_zip.writestr(nome_arquivo, buffer.getvalue())

                        dados_disponiveis = True  # Defina a flag como True, indicando que há dados disponíveis para pelo menos um funcionário

                if not dados_disponiveis:
                    
                    return None

            # Volte para o início do buffer_zip
            buffer_zip.seek(0)

            # Crie uma resposta com os bytes do buffer_zip
            response = make_response(buffer_zip.read())

            # Defina os cabeçalhos da resposta
            response.headers['Content-Type'] = 'application/zip'
            response.headers['Content-Disposition'] = 'attachment; filename=arquivos_excel.zip'

            return response
    except Exception as e:
        print(f'Erro ao gerar arquivos Excel: {e}')
        return "Erro ao gerar arquivos Excel"


# Função para filtrar os dados do funcionário pelo intervalo de datas especificado
def filtrar_por_datas(dados_funcionario, data_inicio, data_fim):
    try:
        dados_filtrados = [dados for dados in dados_funcionario if data_inicio <= datetime.strptime(dados['data'], '%Y-%m-%d').date() <= data_fim]


        return dados_filtrados
    except Exception as e:
        print(f"Erro ao filtrar por datas: {e}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)