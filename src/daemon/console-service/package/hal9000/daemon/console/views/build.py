from flet_routed_app import MvpViewBuilder

from my_package.views.counter import CounterModel, CounterPresenter, CounterView


class MainViewBuilder(MvpViewBuilder):
    model_class = MainModel
    presenter_class = MainPresenter
    view_class = MainView
