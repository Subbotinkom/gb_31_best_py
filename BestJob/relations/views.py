from django.db.models import Max
from django.shortcuts import render

# Create your views here.
from django.views.generic import ListView, DetailView, TemplateView

from BestJob.settings import UserRole
from cvs.models import CV
from users.models import EmployerProfile, WorkerProfile
from vacancies.models import Vacancy
from .models import Relations, RelationHistory, RelationStatus


class RelationHistoryDetailView(TemplateView):
    template_name = 'relations_detail.html'
    model = RelationStatus

    def get(self, request, *args, **kwargs):
        super(RelationHistoryDetailView, self).get(request, *args, **kwargs)
        context = self.get_context_data()
        if request.user.is_authenticated:
            user = request.user

            relations = list()
            history_lists = list()

            # Работодатель.
            if user.role_id == UserRole.EMPLOYER:

                profile = EmployerProfile.objects.get(user_id=user.pk)
                if profile:
                    vacancies = Vacancy.objects.filter(employer_profile_id=profile.pk).order_by('-created_at')
                    if vacancies:
                        for vacancy in vacancies:
                            relation = Relations.objects.filter(vacancy_id=vacancy.pk).order_by('-updated')
                            if relation:
                                relations.append(relation.first())

            # Соискатель.
            elif user.role_id == UserRole.WORKER:

                profile = WorkerProfile.objects.get(user_id=user.pk)
                if profile:
                    cvs = CV.objects.filter(worker_profile_id=profile.pk).order_by('-date_create')
                    if cvs:
                        for cv in cvs:
                            relation = Relations.objects.filter(cv_id=cv.pk).order_by('-updated')
                            if relation:
                                relations.append(relation.first())

            for relation in relations:
                relation_history = RelationHistory.objects.filter(relation_id=relation.pk,
                                                                  status__for_employer=True).order_by('-status__status_priority')

                # Работодатель.
                if user.role_id == UserRole.EMPLOYER:

                    emp_rel_his = relation_history.filter(status__for_employer=True).order_by('-status__status_priority')

                    if emp_rel_his:
                        relation_history.last_status = emp_rel_his.first().status.name
                        relation_history.last_status_date = emp_rel_his.first().created
                # Соискатель.
                elif user.role_id == UserRole.WORKER:

                    work_rel_his = relation_history.filter(status__for_worker=True).order_by('-status__status_priority')
                    if work_rel_his:
                        relation_history.last_status = work_rel_his.first().status.name
                        relation_history.last_status_date = work_rel_his.first().created


                history_lists.append(relation_history)

            context['history_lists'] = history_lists

        else:
            error_message = f'user is not authenticated'
            context['error_message'] = error_message
            print(error_message)

        return self.render_to_response(context)


class LastListView(ListView):
    model = Relations
    template_name = 'relation_last_list.html'


class RelationDetailView(DetailView):
    model = RelationHistory
    template_name = 'relations_detail.html'
