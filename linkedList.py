


class Node:
    def __init__(self, data):
        self.data = data
        self.prox = None
        self.prev = None

    def set_data(self, new_data):
        self.data = new_data
    def get_data(self):
        return self.data

class LinkedList: 
    def __init__ (self) :
        self.head = None
        self.tail = None 

    def add(self, data):
        if self.head == None: 
            self.head = Node(data)
            self.tail = self.head
            self.head.prox = None 
            self.head.prev = None 
        else: 
            novo = Node(data)
            novo.prox = self.head
            novo.prev = None 
            self.head.prev = novo 
            self.head = novo
    def remove_last(self):
        if self.tail == None:
            return
        if self.head == self.tail:
            self.head = None 
            self.tail = None 
            return
        data = self.tail.get_data()
        self.tail = self.tail.prev
        self.tail.prox = None 
        return data

    def __iter__(self):
        atual = self.head 

        while atual is not None:
            yield atual.data 
            atual = atual.prox

    

    
