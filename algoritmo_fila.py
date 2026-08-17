"""
Algoritmo de Fila de Atendimento — Clínica Vida+
Passo 4 do Projeto Integrado

Regra: O primeiro que chega é o primeiro a ser atendido (FIFO)
"""

class FilaAtendimento:
    def __init__(self):
        self.fila = []
    
    def inserir(self, nome, cpf):
        """Insere paciente no final da fila"""
        paciente = {"nome": nome, "cpf": cpf}
        self.fila.append(paciente)
        print(f"Paciente {nome} entrou na fila. Posição: {len(self.fila)}")
        return True
    
    def remover(self):
        """Remove o primeiro paciente da fila para atendimento"""
        if not self.fila:
            print("Fila vazia! Nenhum paciente para atender.")
            return None
        
        atendido = self.fila.pop(0)
        print(f"Paciente {atendido['nome']} foi chamado para atendimento.")
        return atendido
    
    def mostrar_fila(self):
        """Mostra quem está na fila"""
        if not self.fila:
            print("Fila vazia.")
            return []
        
        print("\n--- PACIENTES NA FILA ---")
        for i, p in enumerate(self.fila, 1):
            print(f"{i}. {p['nome']} (CPF: {p['cpf']})")
        return self.fila
    
    def tamanho(self):
        return len(self.fila)


# Demonstração do algoritmo
if __name__ == "__main__":
    fila = FilaAtendimento()
    
    # 1. Inserir 3 pacientes na fila
    print("=" * 50)
    print("SISTEMA DE FILA — CLÍNICA VIDA+")
    print("=" * 50)
    
    fila.inserir("João Silva", "123.456.789-00")
    fila.inserir("Maria Santos", "987.654.321-00")
    fila.inserir("Pedro Oliveira", "456.789.123-00")
    
    # Mostrar fila
    fila.mostrar_fila()
    
    # 2. Remover o primeiro paciente para atendimento
    print("\n--- CHAMANDO PRÓXIMO PACIENTE ---")
    atendido = fila.remover()
    
    # 3. Mostrar quem ainda está na fila
    print("\n--- FILA ATUALIZADA ---")
    fila.mostrar_fila()
    
    print(f"\nTotal na fila: {fila.tamanho()} paciente(s)")
