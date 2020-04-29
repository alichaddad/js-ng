from .resource import ResourceParser


class Billing:
    def __init__(self, explorer):
        self._explorer = explorer

    def reservation_resources(self, reservation):
        """compute how much resource units is reserved in the reservation

        Args:
            reservation ([type]): reservation object

        Returns:
            list: list of ResourceUnitsNode object
        """
        rp = ResourceParser(self._explorer, reservation)
        return rp.calculate_used_resources()

    def reservation_resources_cost(self, reservation):
        """compute how much resource units is reserved in the reservation

        Args:
            reservation ([type]): reservation object

        Returns:
            list: list of ResourceUnitsNode object with costs filled in
        """
        rp = ResourceParser(self._explorer, reservation)
        return rp.calculate_used_resources_cost()

    def payout_farmers(self, client, reservation):
        """payout farmer based on the resources per node used

        Args:
            client ([type]): tfchain wallet or stellar client
            reservation ([type]): reservation object

        Returns:
            list: list of transactions
        """
        rp = ResourceParser(self._explorer, reservation)
        costs = rp.calculate_used_resources_cost()
        return rp.payout_farmers(client, costs, reservation.id)

    def verify_payments(self, client, reservation):
        """verify that a reservation with a given ID has been paid for, for all farms belonging to the current user 3bot

        Args:
            client ([type]): tfchain wallet or stellar client
            reservation ([type]): reservation object

        Returns:
            bool: True if the reservation has been fully funded for the farms owned by the current user 3bot
        """
        rp = ResourceParser(self._explorer, reservation)
        return rp.validate_reservation_payment(client, reservation.id)
