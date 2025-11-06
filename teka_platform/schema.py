import graphene
from core.schema import Query as CoreQuery, Mutation as CoreMutation


class Query(CoreQuery):
    pass


class Mutation(CoreMutation):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)