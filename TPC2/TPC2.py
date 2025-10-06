# %%
import random
print("Bem vindo ao jogo dos 21 fósforos! O jogo consiste em retirar 1,2,3 ou 4 dos 21 fósforos e quem retirar o último PERDE! ")
jogador=input("Queres jogar em primeiro ou em segundo lugar?")
n=21

if jogador=="Primeiro" or jogador=="primeiro":
    while n>5:
        x=int(input("Quantos fósforos queres retirar?"))
        if x>4 or x<1:
            print("Não podes!")
            continue
        else:
            n=n-x
            print(f"Retiraste {x} fósforos, ficaram {n}.")
            computador=5-x
            n=n-computador
            print(f"O computador retirou {computador} fósforos. Agora tens {n} quantos tiras?")
    print("Agora só consegues tirar o último...Perdeste!")      

elif jogador=="Segundo" or jogador=="segundo" :
    comp=random.randint(1,4)
    n=n-comp
    print(f"O computador retirou {comp} fósforos. Sobraram {n}.")

    while n>1:
        y=int(input("Quantos fósforos queres retirar?"))
        while (y>4 or y<1 or y>n):
            print("Erro.")
            y=int(input("Diz um número de 1 a 4")) 


        n-=y
        print(f"Retiraste {y} fósforos. Tens {n}.")

        if n==1:
            print("Ganhaste!")
            break
           
        if n % 5 != 1:
            comp = (n - 1) % 5
            if comp == 0:
                y = random.randint(1, min(4,n-1))
        else:
            comp = random.randint(1, min(4,n-1))

        n -= y
        print(f"O computador retirou {y} fósforos. Tens {n}.")     

        if n == 1:
            print("Perdeste")
            break  
else:
    print("Escolhe direito.")         






